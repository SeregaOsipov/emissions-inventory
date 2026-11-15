#!/usr/bin/env python

# %load_ext autoreload
# %autoreload 2

import os
import subprocess
from netCDF4 import Dataset
import xarray as xr
import numpy as np
from warnings import warn as warning

from preproc.preproc_utils import get_grid_area, write_netcdf, EDGAR_EIGHT_SECTORS, unzip_edgar_files, \
    EDGAR_IPCC_SECTORS

# ============== README ======================
"""
v8.1
website https://edgar.jrc.ec.europa.eu/dataset_ap81
downloading: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v81_FT2022_AP_new/
I need emissions units to be: "kg m-2 s-1". So take Emission Flux file (_flx.nc)

Run in terminal:
cd /work/mm0062/b302074/workspace/python/hermesv3_gr
gogomamba
mamba activate py311_hermes
python -u preproc/edgar_v81_ap_preproc.py >& log.edgar_v81_ap_preproc


USE UNIFIED edgar_v81_preproc.py for GHG, APs, GHG

"""

# To do yearly emissions
PROCESS_YEARLY = True  # False
PROCESS_MONTHLY = False  # True

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/project/k10048/osipovs/Data/emissions/EDGAR/v81_FT2022_AP_new/'
OUTPUT_PATH = INPUT_PATH + '/hermes_pp/'
LIST_POLLUTANTS = ['BC', 'CO', 'NH3', 'NOx', 'OC', 'PM10', 'PM2.5', 'SO2', 'NMVOC']
LIST_YEARS = [2022]

MONTHLY_INPUT_NAME = 'monthly/<pollutant>/bkl_<sector>/v8.1_FT2022_AP_<pollutant>_<year>_bkl_<sector>_flx.nc'  # month is a time dimension
ARCHIVE_MONTHLY_INPUT_NAME = 'monthly/<pollutant>/bkl_<sector>/bkl_<sector>_flx_nc.zip'

YEARLY_INPUT_NAME = '<pollutant>/<sector>/flx_nc/v8.1_FT2022_AP_<pollutant>_<year>_<sector>_flx.nc'
ARCHIVE_YEARLY_INPUT_NAME = '<pollutant>/<sector>/flx_nc/v8.1_FT2022_AP_<pollutant>_<year>_<sector>_flx_nc.zip'
# ==============================================================


def do_monthly_transformation(year, pollutants, sectors):

    # year=2023
    # sectors=EDGAR_MONTHLY_SECTORS
    # sector=sectors[0]
    # pollutant='CH4'
    # month=1

    for pollutant in pollutants:
        print('Processing pollutant {}'.format(pollutant))
        for sector in sectors:  # ipcc in list(ipcc_to_sector_dict().keys()):
            # sector = ipcc_to_sector_dict()[ipcc]
            print('\t sector {}'.format(sector))
            for month in range(1, 12 + 1, 1):
                file_path = os.path.join(INPUT_PATH,  MONTHLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<month>', str(month)).replace('<sector>', sector))

                if os.path.exists(file_path):
                    grid_area = get_grid_area(file_path)
                    print('in: {}'.format(file_path))
                    # nc_in = Dataset(file_path, mode='r')
                    nc_in = xr.open_dataset(file_path)
                    nc_in = nc_in.isel(time=(nc_in.time.dt.month==month))  #  EDGAR stores 12 month in a single file

                    pollutant = pollutant.replace('.', '')  # PM2.5 case

                    data = np.array(nc_in.fluxes)
                    lats = nc_in.lat
                    lons = nc_in.lon
                    nc_in.close()

                    data_attributes = {'long_name': pollutant.lower(),
                                       'units': 'kg.m-2.s-1',
                                       'coordinates': 'lat lon',
                                       'grid_mapping': 'crs'}

                    out_path_aux = os.path.join(OUTPUT_PATH, 'monthly_mean', pollutant.lower() + '_' + sector.lower())
                    if not os.path.exists(out_path_aux):
                        os.makedirs(out_path_aux)
                    nc_file_path = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(pollutant.lower(), year, str(month).zfill(2)))
                    print('Writing to {}'.format(nc_file_path))
                    write_netcdf(nc_file_path, data, data_attributes, lats, lons, grid_area, year, sector.lower())
                else:
                    # warning("The pollutant {} for the sector {} does not exist.\n File not found: {}".format(pollutant, sector, file_path))
                    raise Exception("The pollutant {} for the sector {} does not exist.\n File not found: {}".format(pollutant, sector, file_path))
    return True


def do_yearly_transformation(year, pollutants, sectors):
    # year=2023
    # sectors=EDGAR_MONTHLY_SECTORS
    # sector=sectors[0]
    # pollutant='CH4'
    # month=1

    for pollutant in pollutants:
        print('Processing pollutant {}'.format(pollutant))
        for sector in sectors:
            print('\t sector {}'.format(sector))
            file_path = os.path.join(INPUT_PATH,  YEARLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<sector>', sector))

            if os.path.exists(file_path):
                grid_area = get_grid_area(file_path)
                print('in: {}'.format(file_path))
                # nc_in = Dataset(file_path, mode='r')
                nc_in = xr.open_dataset(file_path)

                pollutant = pollutant.replace('.', '')  # PM2.5 case

                data = np.array(nc_in.fluxes)
                lats = nc_in.lat
                lons = nc_in.lon
                nc_in.close()

                data_attributes = {'long_name': pollutant.lower(),
                                   'units': 'kg.m-2.s-1',
                                   'coordinates': 'lat lon',
                                   'grid_mapping': 'crs'}

                out_path_aux = os.path.join(OUTPUT_PATH, 'yearly_mean', pollutant.lower() + '_' + sector.lower())
                if not os.path.exists(out_path_aux):
                    os.makedirs(out_path_aux)
                nc_file_path = os.path.join(out_path_aux, '{0}_{1}.nc'.format(pollutant.lower(), year))
                print('Writing to {}'.format(nc_file_path))
                write_netcdf(nc_file_path, data, data_attributes, lats, lons, grid_area, year, sector.lower())
            else:
                warning("The pollutant {} for the sector {} does not exist.\n File not found: {}".format(pollutant, sector, file_path))
    return True


if __name__ == '__main__':
    if PROCESS_MONTHLY:
        print('Process Monthly')
        unzip_edgar_files(None, LIST_POLLUTANTS, EDGAR_EIGHT_SECTORS, INPUT_PATH, ARCHIVE_MONTHLY_INPUT_NAME)  # do it only once
        for year in LIST_YEARS:
            do_monthly_transformation(year, LIST_POLLUTANTS, EDGAR_EIGHT_SECTORS)

    if PROCESS_YEARLY:
        print('Process Yearly')

        for year in LIST_YEARS:
            print('Year {}'.format(year))
            # unzip_edgar_files(year, LIST_POLLUTANTS, EDGAR_IPCC_SECTORS, INPUT_PATH, ARCHIVE_YEARLY_INPUT_NAME)  # do it only once
            do_yearly_transformation(year, LIST_POLLUTANTS, EDGAR_IPCC_SECTORS)

    print('DONE')


