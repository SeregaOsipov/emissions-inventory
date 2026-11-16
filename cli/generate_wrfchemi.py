#!/usr/bin/env python
"""
Domain-agnostic CLI wrapper around HERMESv3_GR for WRF-Chem wrfchemi generation.

Derives Lambert Conformal Conic (LCC) grid parameters directly from a WRF geo_em
file, guards cold-start auxiliary initialization, handles NRT CAMS-GFAS fallback
and shipping Feb-29 mapping inside an ephemeral staging workspace, and validates
the output NetCDF before writing atomically to --out-file.
"""

from __future__ import annotations

import argparse
import configparser
import csv
from datetime import date, datetime, timedelta, timezone
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import netCDF4 as nc
import numpy as np
from pyproj import Proj
import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_runtime_paths(repo_root: Path, work_dir_override: Path | None = None) -> dict[str, Path]:
    cfg_path = repo_root / "config.yaml"
    cfg = {}
    if cfg_path.is_file():
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    paths_cfg = cfg.get("paths", {})

    work_dir = Path(
        work_dir_override
        or os.environ.get("HERMES_WORK_DIR")
        or paths_cfg.get("hermes_work_dir", "/HDD1/Data/emissions/hermes")
    )
    data_root = Path(
        os.environ.get("EMISSIONS_DATA_ROOT")
        or paths_cfg.get("emissions_data_root", str(work_dir.parent))
    )
    if work_dir_override is not None:
        input_dir = work_dir / "HERMES_IN"
        data_path = work_dir / "datasets"
        output_dir = work_dir / "HERMES_OUT"
    else:
        input_dir = Path(paths_cfg.get("hermes_input_dir", work_dir / "HERMES_IN"))
        data_path = Path(paths_cfg.get("hermes_data_path", work_dir / "datasets"))
        output_dir = Path(paths_cfg.get("hermes_output_dir", work_dir / "HERMES_OUT"))

    return {
        "work_dir": work_dir,
        "data_root": data_root,
        "input_dir": input_dir,
        "data_path": data_path,
        "output_dir": output_dir,
    }


def _load_runtime_config(repo_root: Path) -> dict:
    cfg_path = repo_root / "config.yaml"
    if not cfg_path.is_file():
        return {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("runtime", {}) or {}


def _resolve_ntasks(
    ntasks: int | None,
    cluster: str | None,
    expected_nx: int,
    runtime_cfg: dict,
) -> tuple[int, str]:
    eff_cluster = str(
        cluster
        or os.environ.get("HERMES_CLUSTER")
        or runtime_cfg.get("default_cluster")
        or "local_workstation"
    )
    clusters_cfg = runtime_cfg.get("clusters", {}) or {}
    cluster_ntasks = (clusters_cfg.get(eff_cluster) or {}).get("ntasks")
    env_tasks = (
        os.environ.get("HERMES_NTASKS")
        or os.environ.get("NTASKS")
        or os.environ.get("SLURM_NTASKS")
    )
    if ntasks is not None:
        req_tasks = int(ntasks)
    elif env_tasks:
        req_tasks = int(env_tasks)
    elif cluster_ntasks is not None:
        req_tasks = int(cluster_ntasks)
    else:
        req_tasks = 6
    eff_tasks = max(1, min(req_tasks, expected_nx // 2))
    return eff_tasks, eff_cluster


def derive_lcc_from_geo_em(geo_em_path: Path) -> dict[str, float | int | str]:
    """Computes HERMESv3 LccGrid parameters matching a WRF geo_em NetCDF grid."""
    with nc.Dataset(geo_em_path, "r") as ds:
        map_proj = getattr(ds, "MAP_PROJ", 1)
        if int(map_proj) != 1:
            raise ValueError(f"{geo_em_path} uses MAP_PROJ={map_proj}; only Lambert Conformal (1) is supported.")
        lat_1 = float(ds.TRUELAT1)
        lat_2 = float(ds.TRUELAT2)
        lon_0 = float(ds.STAND_LON)
        dx = float(ds.DX)
        dy = float(ds.DY)
        nx = int(ds.dimensions["west_east"].size)
        ny = int(ds.dimensions["south_north"].size)
        xlat00 = float(ds.variables["XLAT_M"][0, 0, 0])
        xlon00 = float(ds.variables["XLONG_M"][0, 0, 0])

    proj = Proj(
        proj="lcc",
        ellps="WGS84",
        R=6370000.0,
        a=6370000.0,
        lat_1=lat_1,
        lat_2=lat_2,
        lon_0=lon_0,
        lat_0=lat_1,
        to_meter=1,
        x_0=0,
        y_0=0,
        k_0=1.0,
    )
    xc0, yc0 = proj(xlon00, xlat00)
    return {
        "domain_type": "lcc",
        "lat_1": lat_1,
        "lat_2": lat_2,
        "lon_0": lon_0,
        "lat_0": lat_1,
        "nx": nx,
        "ny": ny,
        "inc_x": dx,
        "inc_y": dy,
        "x_0": xc0 - dx / 2.0,
        "y_0": yc0 - dy / 2.0,
    }


def build_isolated_mpi_env(hermes_python: Path, repo_root: Path) -> dict[str, str]:
    """Constructs a subprocess environment isolated from Intel oneAPI MPI runtime variables."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("I_MPI_")}
    hermes_env_dir = hermes_python.resolve().parent.parent
    hermes_bin = str(hermes_env_dir / "bin")
    hermes_lib = str(hermes_env_dir / "lib")

    def _clean_path(raw: str, prepend: str) -> str:
        parts = [p for p in raw.split(os.pathsep) if p and "oneapi" not in p.lower() and p != prepend]
        return os.pathsep.join([prepend] + parts)

    env["PATH"] = _clean_path(env.get("PATH", ""), hermes_bin)
    env["LD_LIBRARY_PATH"] = _clean_path(env.get("LD_LIBRARY_PATH", ""), hermes_lib)
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{repo_root / 'models' / 'hermesv3_gr'}"
    return env


def _ensure_gfas_day(
    cand_dt: datetime,
    gfas_raw_dir: Path,
    gfas_pp_dir: Path,
    repo_root: Path,
    hermes_python: Path,
    sub_env: dict[str, str],
    allow_download: bool = True,
) -> Path | None:
    compact = cand_dt.strftime("%Y%m%d")
    iso = cand_dt.strftime("%Y-%m-%d")
    nc_file = gfas_pp_dir / "daily_mean" / "multivar" / f"ga_{compact}.nc"
    if nc_file.is_file() and nc_file.stat().st_size > 0:
        return nc_file

    grb_file = gfas_raw_dir / f"ga_{compact}.grb"
    if not grb_file.is_file() or grb_file.stat().st_size == 0:
        if not allow_download:
            return None
        try:
            gfas_raw_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    str(hermes_python),
                    str(repo_root / "downloading" / "download_CAMS_GFAS.py"),
                    "--start_date", iso,
                    "--end_date", iso,
                    "--output_dir", str(gfas_raw_dir),
                    "--workers", "1",
                    "--chunk_days", "1",
                ],
                env=sub_env,
                check=True,
                timeout=600,
            )
        except Exception as exc:
            print(f"[HERMES-CLI] GFAS ADS fetch skipped/unavailable for {iso}: {exc}", flush=True)
            return None

    if not grb_file.is_file() or grb_file.stat().st_size == 0:
        return None

    try:
        gfas_pp_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                str(hermes_python),
                str(repo_root / "preproc" / "gfas12_preproc.py"),
                "--in_file_path", str(grb_file),
                "--output_folder_path", str(gfas_pp_dir),
            ],
            env=sub_env,
            check=True,
            timeout=300,
        )
    except Exception as exc:
        print(f"[HERMES-CLI] GFAS preprocessing failed for {iso}: {exc}", flush=True)
        return None

    if nc_file.is_file() and nc_file.stat().st_size > 0:
        return nc_file
    return None


def _resolve_gfas_nrt(
    start_dt: datetime,
    gfas_mode: str,
    gfas_lookback_days: int,
    gfas_raw_dir: Path,
    gfas_pp_dir: Path,
    repo_root: Path,
    hermes_python: Path,
    sub_env: dict[str, str],
) -> tuple[datetime | None, Path | None]:
    if gfas_mode == "off":
        return None, None
    if gfas_mode == "historical":
        nc_file = _ensure_gfas_day(
            start_dt, gfas_raw_dir, gfas_pp_dir, repo_root, hermes_python, sub_env, allow_download=True
        )
        if nc_file is None:
            raise FileNotFoundError(f"Missing GFASv12 file for historical date {start_dt.strftime('%Y-%m-%d')}")
        return start_dt, nc_file

    utc_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    anchor_dt = min(start_dt, utc_today - timedelta(days=1)) if start_dt >= utc_today else start_dt
    candidates = [anchor_dt - timedelta(days=i) for i in range(max(1, gfas_lookback_days + 1))]

    # First check locally preprocessed or GRIB files before hitting ADS network
    for cand in candidates:
        nc_local = _ensure_gfas_day(cand, gfas_raw_dir, gfas_pp_dir, repo_root, hermes_python, sub_env, allow_download=False)
        if nc_local is not None:
            return cand, nc_local

    for cand in candidates:
        nc_remote = _ensure_gfas_day(cand, gfas_raw_dir, gfas_pp_dir, repo_root, hermes_python, sub_env, allow_download=True)
        if nc_remote is not None:
            return cand, nc_remote

    raise RuntimeError(
        f"Unable to obtain any CAMS-GFAS file within lookback window "
        f"{candidates[-1].strftime('%Y-%m-%d')}..{candidates[0].strftime('%Y-%m-%d')}"
    )


def _prepare_cross_table(
    src_cross_table: Path,
    tmp_dir: Path,
    start_dt: datetime,
    data_path: Path,
    gfas_raw_dir: Path,
    gfas_pp_dir: Path,
    gfas_mode: str,
    gfas_lookback_days: int,
    repo_root: Path,
    hermes_python: Path,
    sub_env: dict[str, str],
) -> Path:
    with open(src_cross_table, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))

    if not rows:
        raise ValueError(f"Empty cross_table CSV: {src_cross_table}")

    header = rows[0]
    col_idx = {name: i for i, name in enumerate(header)}
    start_compact = start_dt.strftime("%Y%m%d")
    is_feb29 = start_dt.month == 2 and start_dt.day == 29

    chosen_gfas_dt, chosen_gfas_nc = _resolve_gfas_nrt(
        start_dt, gfas_mode, gfas_lookback_days, gfas_raw_dir, gfas_pp_dir, repo_root, hermes_python, sub_env
    )
    gfas_stage_dir = tmp_dir / "gfas_stage" / "daily_mean"
    if chosen_gfas_nc is not None and chosen_gfas_dt != start_dt:
        mv_dir = gfas_stage_dir / "multivar"
        mv_dir.mkdir(parents=True, exist_ok=True)
        (mv_dir / f"ga_{start_compact}.nc").symlink_to(chosen_gfas_nc)
        print(
            f"[HERMES-CLI] GFASv12 NRT persist: {start_dt.strftime('%Y-%m-%d')} -> "
            f"{chosen_gfas_nc.name}",
            flush=True,
        )

    ship_stage_dir = tmp_dir / "ship_stage" / "daily_mean"
    for r in rows[1:]:
        if len(r) < len(header):
            continue
        ei = r[col_idx["ei"]]
        active = str(r[col_idx["active"]]).strip() == "1"
        if not active:
            continue

        if ei.startswith("GFAS"):
            if gfas_mode == "off":
                r[col_idx["active"]] = "0"
            elif chosen_gfas_nc is not None and chosen_gfas_dt != start_dt:
                r[col_idx["path"]] = str(gfas_stage_dir)
            continue

        if r[col_idx["frequency"]] == "daily" and r[col_idx["source_type"]] == "area":
            ref_year = str(r[col_idx["ref_year"]]).strip()
            raw_path = r[col_idx["path"]].replace("<data_path>", str(data_path))
            pols = [p.strip() for p in r[col_idx["pollutants"]].split(",") if p.strip()]
            mmdd = start_dt.strftime("%m%d")

            if is_feb29:
                for pol in pols:
                    src_f = Path(raw_path) / pol / f"{pol}_{ref_year}0228.nc"
                    if not src_f.is_file():
                        raise FileNotFoundError(f"Missing daily area input {src_f} for Feb-29 mapping")
                    dst_dir = ship_stage_dir / pol
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    dst_f = dst_dir / f"{pol}_{ref_year}0229.nc"
                    if not dst_f.exists():
                        dst_f.symlink_to(src_f)
                r[col_idx["path"]] = str(ship_stage_dir)
            else:
                missing = [
                    str(Path(raw_path) / pol / f"{pol}_{ref_year}{mmdd}.nc")
                    for pol in pols
                    if not (Path(raw_path) / pol / f"{pol}_{ref_year}{mmdd}.nc").is_file()
                ]
                if missing:
                    raise FileNotFoundError(
                        f"Missing {len(missing)} daily {ei} file(s) for {ref_year}{mmdd}: {missing[:3]}"
                    )

    ephemeral_csv = tmp_dir / "EI_configuration.csv"
    with open(ephemeral_csv, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";").writerows(rows)
    return ephemeral_csv


def _write_run_conf(
    base_conf: Path,
    tmp_dir: Path,
    paths: dict[str, Path],
    cross_table: Path,
    start_dt: datetime,
    days: int,
    lcc_params: dict[str, float | int | str] | None,
    conf_name: str = "hermes_run.conf",
    out_sub: str = "out",
) -> tuple[Path, Path]:
    cp = configparser.ConfigParser(inline_comment_prefixes=("#", ";"), interpolation=None)
    cp.optionxform = str
    cp.read(base_conf, encoding="utf-8")

    out_dir = tmp_dir / out_sub
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)

    cp["GENERAL"]["input_dir"] = str(paths["input_dir"])
    cp["GENERAL"]["data_path"] = str(paths["data_path"])
    cp["GENERAL"]["output_dir"] = str(out_dir)
    cp["GENERAL"]["output_name"] = "HERMESv3_<date>.nc"
    cp["GENERAL"]["start_date"] = start_dt.strftime("%Y/%m/%d 00:00:00")
    if "end_date" in cp["GENERAL"]:
        del cp["GENERAL"]["end_date"]
    cp["GENERAL"]["output_timestep_type"] = "daily"
    cp["GENERAL"]["output_timestep_num"] = str(days)
    cp["GENERAL"]["output_timestep_freq"] = "1"
    cp["GENERAL"]["first_time"] = "0"
    cp["GENERAL"]["erase_auxiliary_files"] = "0"

    if lcc_params is not None:
        cp["DOMAIN"]["domain_type"] = "lcc"
        for k in ("lat_1", "lat_2", "lon_0", "lat_0", "nx", "ny", "inc_x", "inc_y", "x_0", "y_0"):
            cp["DOMAIN"][k] = str(lcc_params[k])
        aux_rel = f"WRF_CHEM_<domain_type>_<resolution>_{lcc_params['nx']}_{lcc_params['ny']}"
        cp["DOMAIN"]["auxiliary_files_path"] = str(paths["output_dir"] / "auxiliary_files" / aux_rel)
        aux_dir = paths["output_dir"] / "auxiliary_files" / (
            f"WRF_CHEM_lcc_{float(lcc_params['inc_x'])}_{float(lcc_params['inc_y'])}"
            f"_{lcc_params['nx']}_{lcc_params['ny']}"
        )
    else:
        nx = int(float(cp["DOMAIN"]["nx"]))
        ny = int(float(cp["DOMAIN"]["ny"]))
        inc_x = float(cp["DOMAIN"]["inc_x"])
        inc_y = float(cp["DOMAIN"]["inc_y"])
        aux_raw = cp["DOMAIN"]["auxiliary_files_path"]
        aux_dir = Path(
            aux_raw.replace("<domain_type>", cp["DOMAIN"]["domain_type"]).replace("<resolution>", f"{inc_x}_{inc_y}")
        )

    cp["EMISSION_INVENTORY_CONFIGURATION"]["cross_table"] = str(cross_table)

    conf_path = tmp_dir / conf_name
    with open(conf_path, "w", encoding="utf-8") as f:
        cp.write(f)
    return conf_path, aux_dir


def _write_cold_start_csv(base_csv: Path, dst_csv: Path) -> None:
    """Writes header + first active yearly point-source row with temporal profiles for --first_time True."""
    with open(base_csv, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    if not rows:
        raise ValueError(f"Empty cross_table CSV: {base_csv}")
    header = rows[0]
    col_idx = {name: i for i, name in enumerate(header)}
    selected = [header]
    for r in rows[1:]:
        if len(r) < len(header):
            continue
        if (
            r[col_idx["active"]].strip() == "1"
            and r[col_idx["source_type"]].strip() == "point"
            and r[col_idx["frequency"]].strip() == "yearly"
            and any(r[col_idx[k]].strip() for k in ("p_month", "p_week", "p_day", "p_hour"))
        ):
            selected.append(r)
            break
    with open(dst_csv, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";").writerows(selected)


def validate_hermes_output(nc_path: Path, expected_nx: int, expected_ny: int, expected_days: int) -> None:
    """Checks grid dimensions, timestep count, species count, and NaN absence."""
    with nc.Dataset(nc_path, "r") as ds:
        nx = int(ds.dimensions["west_east"].size)
        ny = int(ds.dimensions["south_north"].size)
        nt = int(ds.dimensions["Time"].size)
        if nx != expected_nx or ny != expected_ny:
            raise ValueError(f"{nc_path}: grid mismatch ({nx}x{ny} != {expected_nx}x{expected_ny})")
        if nt != expected_days:
            raise ValueError(f"{nc_path}: Time length {nt} != {expected_days}")
        e_vars = [v for v in ds.variables if v.startswith("E_")]
        if len(e_vars) < 30:
            raise ValueError(f"{nc_path}: expected >=30 E_* variables, found {len(e_vars)}")
        for chk_var in ("E_CO", "E_NO", "E_SO2"):
            if chk_var not in ds.variables:
                raise ValueError(f"{nc_path}: missing required species {chk_var}")
            if np.isnan(ds.variables[chk_var][:]).any():
                raise ValueError(f"{nc_path}: NaN detected in {chk_var}")


def generate_wrfchemi(
    start_date: str,
    days: int | None = None,
    end_date: str | None = None,
    geo_em: Path | None = None,
    conf: Path | None = None,
    cross_table: Path | None = None,
    out_file: Path | None = None,
    domain_tag: str | None = None,
    ntasks: int | None = None,
    cluster: str | None = None,
    gfas_mode: str = "nrt_persist",
    gfas_lookback_days: int = 5,
    work_dir: Path | None = None,
) -> Path:
    repo_root = _repo_root()
    paths = _load_runtime_paths(repo_root, work_dir_override=work_dir)
    runtime_cfg = _load_runtime_config(repo_root)
    hermes_python = Path(os.environ.get("HERMES_PYTHON") or sys.executable)
    hermes_entry = repo_root / "models" / "hermesv3_gr" / "hermesv3_gr" / "hermes.py"
    base_conf = Path(conf) if conf else (repo_root / "conf" / "hermes_2023.conf")
    base_csv = Path(cross_table) if cross_table else (repo_root / "conf" / "EI_configuration_WRF_Chem_2023.csv")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date is not None:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        num_days = (end_dt - start_dt).days + 1
    elif days is not None:
        num_days = int(days)
    else:
        num_days = 1
    if num_days < 1:
        raise ValueError(f"Invalid step count num_days={num_days}")

    lcc_params = derive_lcc_from_geo_em(Path(geo_em)) if geo_em is not None else None
    if lcc_params is not None:
        expected_nx = int(lcc_params["nx"])
        expected_ny = int(lcc_params["ny"])
    else:
        cp_tmp = configparser.ConfigParser(inline_comment_prefixes=("#", ";"), interpolation=None)
        cp_tmp.read(base_conf, encoding="utf-8")
        expected_nx = int(float(cp_tmp["DOMAIN"]["nx"]))
        expected_ny = int(float(cp_tmp["DOMAIN"]["ny"]))

    eff_tasks, eff_cluster = _resolve_ntasks(ntasks, cluster, expected_nx, runtime_cfg)

    tag = domain_tag or (Path(geo_em).stem.replace(".", "_") if geo_em else "custom")
    target_out = Path(out_file) if out_file else (
        paths["output_dir"] / f"HERMESv3_radm2_madesorgam_{start_dt.strftime('%Y%m%d')}_{tag}.nc"
    )
    target_out.parent.mkdir(parents=True, exist_ok=True)

    sub_env = build_isolated_mpi_env(hermes_python, repo_root)
    mpirun_bin = str(hermes_python.resolve().parent / "mpirun")
    gfas_raw_dir = paths["data_root"] / "CAMS-GFAS"
    gfas_pp_dir = Path(os.path.realpath(paths["data_path"] / "ecmwf" / "gfas"))

    with tempfile.TemporaryDirectory(prefix="hermes_cli_") as tmp:
        tmp_dir = Path(tmp)
        ephemeral_csv = _prepare_cross_table(
            base_csv,
            tmp_dir,
            start_dt,
            paths["data_path"],
            gfas_raw_dir,
            gfas_pp_dir,
            gfas_mode,
            gfas_lookback_days,
            repo_root,
            hermes_python,
            sub_env,
        )
        run_conf, aux_dir = _write_run_conf(
            base_conf, tmp_dir, paths, ephemeral_csv, start_dt, num_days, lcc_params
        )
        aux_dir.mkdir(parents=True, exist_ok=True)
        lock_path = aux_dir / ".hermes_aux.lock"
        print(f"[HERMES-CLI] Acquiring domain auxiliary lock {lock_path}...", flush=True)
        with open(lock_path, "w", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            (aux_dir / "shapefile").mkdir(parents=True, exist_ok=True)
            (aux_dir / f"shapefiles_n{eff_tasks}").mkdir(parents=True, exist_ok=True)

            # Avoid first-run temporal_coords.nc / timezones.nc MPI barrier race when aux_dir is fresh;
            # keep one yearly point row so --first_time True creates both without unused Weight_Matrix_*_1.nc builds.
            if not (aux_dir / "temporal_coords.nc").is_file() or not (aux_dir / "timezones.nc").is_file():
                init_csv = tmp_dir / "init_cross_table.csv"
                _write_cold_start_csv(base_csv, init_csv)
                init_conf, _ = _write_run_conf(
                    base_conf,
                    tmp_dir,
                    paths,
                    init_csv,
                    start_dt,
                    1,
                    lcc_params,
                    conf_name="hermes_init.conf",
                    out_sub="init_out",
                )
                print(f"[HERMES-CLI] Initializing cold-start auxiliary grid files in {aux_dir} (1 rank)...", flush=True)
                subprocess.run(
                    [mpirun_bin, "-np", "1", str(hermes_python), str(hermes_entry), "-c", str(init_conf), "--first_time", "True"],
                    env=sub_env,
                    check=True,
                )

            if os.environ.get("SLURM_JOB_ID"):
                mpi_prefix = ["srun", "-n", str(eff_tasks), "--hint=nomultithread", "--cpu_bind=core"]
            else:
                mpi_prefix = [mpirun_bin, "-np", str(eff_tasks)]

            print(
                f"[HERMES-CLI] Running HERMESv3 ({eff_tasks} ranks, cluster={eff_cluster}): "
                f"start={start_date}, days={num_days}, grid={expected_nx}x{expected_ny}, gfas={gfas_mode}",
                flush=True,
            )
            subprocess.run(
                mpi_prefix + [str(hermes_python), str(hermes_entry), "-c", str(run_conf)],
                env=sub_env,
                check=True,
            )

            produced = tmp_dir / "out" / f"HERMESv3_{start_dt.strftime('%Y%m%d')}.nc"
            if not produced.is_file():
                raise FileNotFoundError(f"Expected HERMES output missing at {produced}")

            validate_hermes_output(produced, expected_nx, expected_ny, num_days)
            tmp_dest = target_out.with_suffix(".nc.tmp")
            shutil.copy2(produced, tmp_dest)
            os.replace(tmp_dest, target_out)
            print(f"[HERMES-CLI] Verified and wrote {target_out}", flush=True)
    return target_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate domain-aligned WRF-Chem emissions via HERMESv3_GR.")
    parser.add_argument("--start-date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=None, help="Number of daily timesteps")
    parser.add_argument("--end-date", default=None, help="Inclusive end date YYYY-MM-DD (alternative to --days)")
    parser.add_argument("--geo-em", type=Path, default=None, help="WRF geo_em.d0X.nc path for automatic LCC derivation")
    parser.add_argument("--conf", type=Path, default=None, help="Base HERMES .conf file")
    parser.add_argument("--cross-table", type=Path, default=None, help="Inventory cross-table CSV")
    parser.add_argument("--out-file", type=Path, default=None, help="Target NetCDF path")
    parser.add_argument("--domain-tag", default=None, help="Tag appended to default output filename")
    parser.add_argument("--ntasks", type=int, default=None, help="MPI rank count override (default from config.yaml runtime.clusters)")
    parser.add_argument("--cluster", default=None, help="Cluster profile name in config.yaml runtime.clusters (e.g., local_workstation, azure_rccg, shaheen)")
    parser.add_argument("--gfas-mode", choices=["nrt_persist", "historical", "off"], default="nrt_persist")
    parser.add_argument("--gfas-lookback-days", type=int, default=5)
    parser.add_argument("--work-dir", type=Path, default=None, help="HERMES work dir root override")
    args = parser.parse_args()

    generate_wrfchemi(
        start_date=args.start_date,
        days=args.days,
        end_date=args.end_date,
        geo_em=args.geo_em,
        conf=args.conf,
        cross_table=args.cross_table,
        out_file=args.out_file,
        domain_tag=args.domain_tag,
        ntasks=args.ntasks,
        cluster=args.cluster,
        gfas_mode=args.gfas_mode,
        gfas_lookback_days=args.gfas_lookback_days,
        work_dir=args.work_dir,
    )


if __name__ == "__main__":
    main()
