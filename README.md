# emissions-inventory

HERMESv3_GR anthropogenic and biomass-burning emissions configuration, custom speciation/temporal/vertical profiles, downloading tools, preprocessing scripts, job runners, and post-processing utilities.

## Repository Layout

- `models/hermesv3_gr`: Git submodule tracking `Serega.Osipov/hermesv3_gr` (`middle_east_branch`, `77bbdcf`).
- `config.yaml`: Centralized runtime paths, cluster MPI rank profiles (`local_workstation`, `azure_rccg`, `shaheen`), and THOFA / full-year 2023 run metadata.
- `cli/`: Domain-agnostic WRF-Chem emission generator (`generate_wrfchemi.py`) deriving LCC grid parameters directly from `geo_em.d0*.nc`, and 366-day 2023 fallback climatology builder (`build_climatology_2023.py`).
- `conf/`: HERMES `.conf` run configs and `EI_configuration_*.csv` inventory tables.
- `data/`: Custom speciation (`Speciation_profile_radm2_madesorgam_WRF_CHEM_AQABA.csv` with `33` WRF-Chem species including `E_CO2` and `E_CH4`), temporal (`TemporalProfile_Weekly_islamic.csv`), vertical profiles, `global_attributes.csv`, and symlinked `gadm_country_mask/`.
- `downloading/`: Dataset downloaders (`download_CAMS_GFAS.py`, `download_edgar_flx_nc.py`, `download_edgar_dataset.sh`).
- `preproc/`: Inventory preprocessing scripts converting raw files to HERMESv3_GR CF-1.6 NetCDF inputs.
- `jobs/`: Unified Slurm (`srun`) + local (`mpirun`) execution scripts (`run_hermes_wrf_domain.sh`, `hermesv3_gr_thofa_2023.sh`, `hermesv3_gr_2023.sh`, `hermesv3_gr_2022.sh`, `hermesv3_gr_2021.sh`, `hermesv3_gr_aqaba_2017.sh`).
- `postproc/`: Diagnostic and analysis scripts (`pp_thofa_emissions.py`, `pp_tropomi_nox_emissions.py`, `nox_emissions_diags.py`, `emissions_pp.py`).

## Environment Setup

```bash
git submodule update --init --recursive
mamba env create -f environment.yml
mamba activate py311_hermes
pip install --no-deps -e ./models/hermesv3_gr
```

## External Data Layout (`/HDD1/Data/emissions`)

Large emission datasets live under `/HDD1/Data/emissions`, with HERMES input/output wiring under `/HDD1/Data/emissions/hermes`:

- `/HDD1/Data/emissions/hermes/HERMES_IN/`: symlinks `conf/`, `data/global_attributes.csv`, `data/profiles/`, and hosts the 515 MB `data/gadm_country_mask/` shapefile.
- `/HDD1/Data/emissions/hermes/datasets/`: symlinks raw/preprocessed inventories (`ecmwf/gfas`, `EDGAR/{2024_GHG,v81_AP,v81_VOC}`, `OMI-HTAP`, `ucar`, `bourtsoukidisetal`, `IASI`, `caseiroetal`, `cams_glob_shipv32`).
- `/HDD1/Data/emissions/hermes/HERMES_OUT/`: WRF-Chem emission NetCDFs (`HERMESv3_radm2_madesorgam_*.nc`), per-rank `logs/`, and cached `auxiliary_files/` (ESMF weight matrices, `temporal_coords.nc`, `timezones.nc`).

## Speciation & `CO2`/`CH4` Implementation

`data/profiles/speciation/Speciation_profile_radm2_madesorgam_WRF_CHEM_AQABA.csv` maps `E_CO2` (`mol.h-1.km-2`) and `E_CH4` alongside RADM2/MADE-SORGAM species (`33` `E_*` variables total):
- `E190`: `CAMS-GLOB-SHIP_v32` (`co2` -> `E_CO2`, `ch4` -> `E_CH4`, plus APs).
- `E700`: `EDGAR_2024_GHG` sectors with both `co2` and `ch4` (`ags`, `che`, `ene`, `ind`, `iro`, `pro_fff`, `rco`, `ref_trf`, `swd_inc`, `tnr_aviation_lto`, `tnr_other`, `tro`).
- `E701`: `EDGAR_2024_GHG` `ch4`-only sectors (`awb`, `enf`, `mnm`, `pro_coal`, `pro_gas`, `pro_oil`, `swd_ldf`, `wwt`).
- `E702`: `EDGAR_2024_GHG` `co2`-only sector (`nmm`).

## Workflow & Verified Outputs

1. **Download & preprocess EDGAR** (`400` `*_flx_nc.zip` archives: `39` `EDGAR_2024_GHG` for `2023`, `164` `v81_FT2022_AP` for `2022`, `197` `v81_FT2022_VOC_spec` for `2022`):
   ```bash
   python downloading/download_edgar_flx_nc.py --workers 8
   PYTHONPATH=. python preproc/edgar_v81_preproc.py --stream EDGAR_2024_GHG --years 2023
   PYTHONPATH=. python preproc/edgar_v81_preproc.py --stream v81_FT2022_AP --years 2022
   PYTHONPATH=. python preproc/edgar_v81_preproc.py --stream v81_FT2022_VOC_spec --years 2022
   ```
   Note: JRC does not publish `voc11` in `FUEL_EXPLOITATION` or `voc16`/`voc20` in `WASTE` for 2022 (`E960`/`E961` handle these).
2. **Download & preprocess CAMS-GFAS** (4-day chunks with `grib_copy` splitting and duplicate `paramId` deduplication; GRIB1 + GRIB2 support with `mami` param `119` falling back to `apt` param `120`; all `366 / 366` `ga_YYYYMMDD.nc` files `2023-01-01`..`2024-01-01` verified on disk):
   ```bash
   python downloading/download_CAMS_GFAS.py --start_date 2023-01-01 --end_date 2024-01-01 --workers 4 --chunk_days 4
   PYTHONPATH=. python preproc/gfas12_preproc.py --start_date 2023-01-01 --end_date 2024-01-01 --workers 8
   ```
3. **Preprocess CAMS-GLOB-SHIP v3.2 (`2022`), OMI-HTAPv2 (`2017`), Wiedinmyer (`2010`)** (`12,410` daily shipping files verified on disk across `34` species × `365` days for `2022`):
   ```bash
   PYTHONPATH=. python preproc/cams_glob_ship_v32_preproc.py --start_date 2022-01-01 --end_date 2022-12-31 --workers 8
   PYTHONPATH=. python preproc/cams_glob_ship_v32_voc_preproc.py --start_date 2022-01-01 --end_date 2022-12-31
   PYTHONPATH=. python preproc/omi_htapV2_preproc.py
   PYTHONPATH=. python preproc/wiedinmyer_preproc.py
   ```
4. **Run HERMESv3_GR**:
   - **THOFA 2023 (`2023-05-15`..`2023-06-30`, 46 steps)**:
     `NTASKS=24 bash jobs/hermesv3_gr_thofa_2023.sh` -> verified **bit-for-bit identical (`MaxAbsDiff = 0.0`) across all `33` `E_*` variables (including `E_CO2` and `E_CH4`)** against `/scratch/Data/AirQuality/THOFA/emissions/HERMESv3_radm2_madesorgam_20230515_THOFA_EDGARv81_GHG.nc`, and bit-for-bit identical on all `32` shared variables against `..._THOFA_EDGARv81.nc`.
   - **Full-Year 2023 (`2023-01-01`..`2024-01-01`, 366 steps)**:
     `NTASKS=24 bash jobs/hermesv3_gr_2023.sh` -> generated and verified `/HDD1/Data/emissions/hermes/HERMES_OUT/HERMESv3_radm2_madesorgam_20230101.nc` (`6,014,787,734` bytes / `5.7 GB`, `Time=366`, `450x450`, `2023-01-01_00:00:00`..`2024-01-01_00:00:00`, all `33` `E_*` species including `E_CO2` and `E_CH4`, `0` `NaN`/`Inf`). Note that single-invocation `output_timestep_num = 366` loads `start_date` once for daily/monthly source files while applying 3D temporal profiles across the year, whereas `end_date > start_date` or `cli/generate_wrfchemi.py` steps daily fire/shipping inputs day-by-day.

## Domain-Agnostic WRF-Chem CLI & 2023 Climatology Builder

For arbitrary WRF `geo_em.d0*.nc` grids (standalone or invoked by external forecasting pipelines):

* **Generate N-day WRF-Chem emissions (`cli/generate_wrfchemi.py` / `jobs/run_hermes_wrf_domain.sh`)**:
  ```bash
  bash jobs/run_hermes_wrf_domain.sh \
    --start-date 2026-11-14 \
    --days 6 \
    --geo-em /path/to/geo_em.d01.nc \
    --out-file /path/to/wrfchemi_d01 \
    --cluster local_workstation \
    --ntasks 6 \
    --gfas-mode nrt_persist
  ```
* **Build 366-day 2023 baseline climatologies (`cli/build_climatology_2023.py`)**:
  ```bash
  python cli/build_climatology_2023.py \
    --geo-em-dir /scratch/Data/AirQuality/domains/qatar_2dom \
    --out-dir /scratch/Data/AirQuality/domains/qatar_2dom/emissions_clim_2023 \
    --cluster local_workstation \
    --ntasks 6 \
    --gfas-mode historical
  ```
