# emissions-inventory

HERMESv3_GR anthropogenic and biomass-burning emissions configuration, custom speciation/temporal/vertical profiles, downloading tools, preprocessing scripts, job runners, and post-processing utilities.

## Repository Layout

- `models/hermesv3_gr`: Git submodule tracking `Serega.Osipov/hermesv3_gr` (`middle_east_branch`).
- `conf/`: HERMES `.conf` run configs and `EI_configuration_*.csv` inventory tables.
- `data/`: Custom speciation, temporal, and vertical profiles, `global_attributes.csv`, and symlinked `gadm_country_mask/`.
- `downloading/`: Dataset downloaders (`download_CAMS_GFAS.py`, `download_edgar_flx_nc.py`, `download_edgar_dataset.sh`).
- `preproc/`: Inventory preprocessing scripts converting raw files to HERMESv3_GR CF-1.6 NetCDF inputs.
- `jobs/`: Unified Slurm + local `mpirun` execution scripts (`hermesv3_gr_thofa_2023.sh`, etc.).
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
- `/HDD1/Data/emissions/hermes/HERMES_OUT/`: WRF-Chem `wrfchemi_*` outputs and auxiliary weight/world-mask caches.

## Reproducing THOFA 2023 (`2023-05-15` to `2023-06-30`)

1. Download CAMS-GFAS daily GRIB files:
   ```bash
   python downloading/download_CAMS_GFAS.py --start_date 2023-05-15 --end_date 2023-06-30
   ```
2. Download EDGAR `EDGAR_2024_GHG`, `v81_FT2022_AP`, and `v81_FT2022_VOC_spec` `*_flx_nc.zip` archives when `jeodpp.jrc.ec.europa.eu` is reachable:
   ```bash
   python downloading/download_edgar_flx_nc.py
   ```
3. Run inventory preprocessors (`preproc/{wiedinmyer_preproc,omi_htapV2_preproc,cams_glob_ship_v32_preproc,cams_glob_ship_v32_voc_preproc,gfas12_preproc,edgar_v81_preproc}.py`).
4. Run HERMESv3_GR locally (`mpirun`) or via `sbatch`:
   ```bash
   bash jobs/hermesv3_gr_thofa_2023.sh
   ```
