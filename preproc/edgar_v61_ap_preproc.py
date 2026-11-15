#!/usr/bin/env python

# Copyright 2018 Earth Sciences Department, BSC-CNS
#
# This file is part of HERMESv3_GR.
#
# HERMESv3_GR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HERMESv3_GR is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HERMESv3_GR. If not, see <http://www.gnu.org/licenses/>.


import os
from netCDF4 import Dataset
import numpy as np
from warnings import warn as warning

from preproc.preproc_utils import ipcc_to_sector_dict, get_grid_area, write_netcdf

# ============== README ======================
"""
v6.1
website https://edgar.jrc.ec.europa.eu/dataset_ap61
downloading: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v61_AP/

Notes:
monthly data extracted from archives was placed into root/monthly

Run in terminal:
cd /work/mm0062/b302074/workspace/python/hermesv3_gr
gogomamba
mamba activate py311_hermes
python -u preproc/edgar_v61_ap_preproc.py >& log.edgar_v61_ap_preproc
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/work/mm0062/b302074/Data/emissions/EDGAR/v61_AP/'
OUTPUT_PATH = INPUT_PATH + '/hermes_pp/'
LIST_POLLUTANTS = ['BC', 'CO', 'NH3', 'NOx', 'OC', 'PM10', 'PM2.5', 'SO2', 'NMVOC']


# To do yearly emissions
PROCESS_YEARLY = False
PROCESS_MONTHLY = True
LIST_YEARS = [2018]  # Only 2018 exist montly.
MONTHLY_INPUT_NAME = 'monthly/<pollutant>/<sector>/EDGARv6.1_<pollutant>_2018_<month>_<sector>.0.1x0.1.nc'
MONTHLY_PATTERN_FILE = 'temporal_profiles/v432_FM_<sector>.0.1x0.1.nc'
ARCHIVE_MONTHLY_INPUT_NAME = '<pollutant>/<sector>/EDGARv6.1_<pollutant>_2018_monthly_<sector>_nc.zip'
# ==============================================================

"""
Main script to transform EDGARv5.0 AP global emission inventory to a NetCDF that follows the CF-1.6 conventions.

This script also calculates the boundaries of teh cells and teh cell area.

Carles Tena Medina (carles.tena@bsc.es) from Barcelona Supercomputing Center (BSC-CNS).
"""


def do_monthly_transformation(year):
    # TODO Documentation
    for pollutant in LIST_POLLUTANTS:
        print('Processing pollutant {}'.format(pollutant))
        for ipcc in list(ipcc_to_sector_dict().keys()):
            sector = ipcc_to_sector_dict()[ipcc]
            print('\t IPCC sector {}'.format(sector))
            for month in range(1, 12 + 1, 1):
                file_path = os.path.join(INPUT_PATH,  MONTHLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<month>', str(month)).replace('<sector>', sector))

                if os.path.exists(file_path):
                    grid_area = get_grid_area(file_path)
                    print('in: {}'.format(file_path))
                    nc_in = Dataset(file_path, mode='r')
                    # print pollutant in ['PM2.5_bio', 'PM2.5_fossil']
                    if pollutant in ['PM2.5',]:
                        aux_pollutant = pollutant.replace('.', '')
                        in_pollutant = 'PM2.5'
                    else:
                        in_pollutant = pollutant
                        aux_pollutant = pollutant

                    data = nc_in.variables['emi_{0}'.format(in_pollutant.lower())][:]

                    data = np.array(data)

                    # Reading lat, lon
                    lats = nc_in.variables['lat'][:]
                    lons = nc_in.variables['lon'][:]
                    nc_in.close()

                    if aux_pollutant in ['PM2.5',]:
                        aux_pollutant = aux_pollutant.replace('.', '')
                    elif aux_pollutant == 'NOx':
                        aux_pollutant = 'nox_no2'

                    data_attributes = {'long_name': aux_pollutant.lower(),
                                       'units': 'kg.m-2.s-1',
                                       'coordinates': 'lat lon',
                                       'grid_mapping': 'crs'}

                    out_path_aux = os.path.join(OUTPUT_PATH, 'monthly_mean', aux_pollutant.lower() + '_' + sector.lower())
                    if not os.path.exists(out_path_aux):
                        os.makedirs(out_path_aux)
                    nc_file_path = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(aux_pollutant.lower(), 2018, str(month).zfill(2)))
                    print('Writing to {}'.format(nc_file_path))
                    write_netcdf(nc_file_path, data, data_attributes, lats, lons, grid_area, 2018, sector.lower())
                else:
                    warning("The pollutant {} for the sector {} (IPCC sector {}) does not exist.\n File not found: {}".format(pollutant, sector, ipcc, file_path))
    return True


if __name__ == '__main__':
    # print('Run the script below in the bash once to extract the archives')
    # for pollutant in LIST_POLLUTANTS:
    #     for ipcc in list(ipcc_to_sector_dict().keys()):
    #         sector = ipcc_to_sector_dict()[ipcc]
    #         archive_file_path = os.path.join(INPUT_PATH, ARCHIVE_MONTHLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<month>', str(month)).replace('<sector>', sector))
    #         output_folder_path = INPUT_PATH + 'monthly/{}/{}'.format(pollutant, sector)
    #         print('mkdir -p {}'.format(output_folder_path))
    #         print('unzip {} -d {}'.format(archive_file_path, output_folder_path))

    # if PROCESS_YEARLY:
    #     for y in LIST_YEARS:
    #         do_yearly_transformation(y)

    if PROCESS_MONTHLY:
        for y in LIST_YEARS:
            if y != 2018:
                raise Exception('EDGAR montly is only 2018')
            do_monthly_transformation()

    print('DONE')


