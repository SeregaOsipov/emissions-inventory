#!/usr/bin/env python
"""
One-time 2023 full-year climatology builder for operational WRF-Chem fallback.

Generates 366-day (2023-01-01 .. 2024-01-01) HERMESv3 emission NetCDFs on each
WRF geo_em domain so operational forecast cycles can slice weekday-aligned
Day-of-Year fallback emissions whenever live generation is unavailable.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cli.generate_wrfchemi import generate_wrfchemi


def build_climatology(
    geo_em_files: list[Path],
    out_dir: Path,
    ntasks: int | None = None,
    cluster: str | None = None,
    gfas_mode: str = "historical",
    overwrite: bool = False,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    for idx, geo_path in enumerate(geo_em_files, start=1):
        m = re.search(r"(d\d+)", geo_path.name)
        dom_id = m.group(1) if m else f"d{idx:02d}"
        out_file = out_dir / f"HERMESv3_radm2_madesorgam_2023_clim_{dom_id}.nc"

        if out_file.is_file() and out_file.stat().st_size > 0 and not overwrite:
            print(f"[Climatology] Skipping existing {out_file}", flush=True)
            outputs.append(out_file)
            continue

        print(f"[Climatology] Building 366-day 2023 baseline for {geo_path} -> {out_file}", flush=True)
        generate_wrfchemi(
            start_date="2023-01-01",
            days=366,
            geo_em=geo_path,
            out_file=out_file,
            domain_tag=f"clim2023_{dom_id}",
            ntasks=ntasks,
            cluster=cluster,
            gfas_mode=gfas_mode,
        )
        outputs.append(out_file)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full-year 2023 (366-day) HERMESv3 fallback NetCDFs per WRF domain.")
    parser.add_argument("--geo-em-dir", type=Path, default=None, help="Directory containing geo_em.d0*.nc files")
    parser.add_argument("--geo-em", type=Path, nargs="+", default=None, help="Explicit list of geo_em files")
    parser.add_argument("--out-dir", type=Path, required=True, help="Target output directory for 2023 climatology NetCDFs")
    parser.add_argument("--ntasks", type=int, default=None, help="MPI rank count per domain (defaults to cluster config in config.yaml)")
    parser.add_argument("--cluster", default=None, help="Cluster profile name in config.yaml runtime.clusters (e.g., local_workstation, azure_rccg, shaheen)")
    parser.add_argument("--gfas-mode", choices=["nrt_persist", "historical", "off"], default="historical")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing 2023 climatology files")
    args = parser.parse_args()

    geo_files: list[Path] = []
    if args.geo_em:
        geo_files = [Path(p) for p in args.geo_em]
    elif args.geo_em_dir:
        geo_files = sorted(args.geo_em_dir.glob("geo_em.d0*.nc"))
    if not geo_files:
        raise FileNotFoundError("No geo_em.d0*.nc files provided via --geo-em or --geo-em-dir")

    build_climatology(
        geo_em_files=geo_files,
        out_dir=args.out_dir,
        ntasks=args.ntasks,
        cluster=args.cluster,
        gfas_mode=args.gfas_mode,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
