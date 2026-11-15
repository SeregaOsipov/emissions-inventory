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


import argparse
import os
import re
from netCDF4 import Dataset
import cf_units
import pandas as pd
import datetime
from datetime import datetime, timedelta

from hermesv3_gr.tools.coordinates_tools import get_grid_area, create_bounds

DEFAULT_INPUT_DIR = os.environ.get('CAMS_GFAS_INPUT_DIR', '/HDD1/Data/emissions/CAMS-GFAS')
DEFAULT_OUTPUT_DIR = os.environ.get('CAMS_GFAS_OUTPUT_DIR', os.path.join(DEFAULT_INPUT_DIR, 'hermesv3_gr_pp'))
DEFAULT_PARAMETERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GFAS_Parameters.csv')

parser = argparse.ArgumentParser(description='Convert daily CAMS-GFAS GRIB files into HERMESv3_GR NetCDF files.')
parser.add_argument("--mode", "--port", help="the are only to support pycharm debugging")
parser.add_argument("--in_file_path", help="Single input GFAS GRIB file path (optional; overrides date range)")
parser.add_argument("--input_dir", default=DEFAULT_INPUT_DIR, help="Directory containing ga_YYYYMMDD.grb files")
parser.add_argument("--output_folder_path", default=DEFAULT_OUTPUT_DIR, help="Output folder path")
parser.add_argument("--parameters_file", help="GFAS_Parameters.csv", default=DEFAULT_PARAMETERS_FILE)
parser.add_argument("--start_date", default="2023-05-15", help="Start date YYYY-MM-DD (used when --in_file_path is omitted)")
parser.add_argument("--end_date", default="2023-06-30", help="End date YYYY-MM-DD (used when --in_file_path is omitted)")
parser.add_argument("--overwrite", action="store_true", help="Overwrite existing ga_YYYYMMDD.nc outputs in batch mode")
args = parser.parse_args()

# ============== README ======================
"""
downloading website: http://apps.ecmwf.int/datasets/data/cams-gfas/
reference: https://www.biogeosciences.net/9/527/2012/

RUN IN BATCH:
sbatch $HERMES_v3/preproc/gfas12_preproc_batch.sh
and then move data to project:
mv /scratch/osipovs/bandwidth/Data/emissions/CAMS-GFAS/hermesv3_gr_pp/daily_mean/multivar/ga_2021* /project/k10048/osipovs/Data/emissions/hermes/datasets/ecmwf/gfas/daily_mean/multivar/

Run on Levante:
gogomamba
python -u ${HERMES3_OLD}/preproc/gfas12_preproc.py
# HERMES3_OLD point to hermes_v3_gr, not *_bsc

Run in terminal on Shaheen:
salloc --partition=shared -n 8 -c 1 --time=8:00:00
ssh node
cd /scratch/osipovs/iops/sw/workspace/hermesv3_gr
source /project/k10066/osipovs/.commonrc; gogomamba; mamba activate py311_hermes
python -u preproc/gfas12_preproc.py >& log.gfas12_preproc
"""

# ============== CONFIGURATION PARAMETERS ======================
# Levante
# INPUT_PATH = '/work/mm0062/b302074/Data/emissions/CAMS-GFAS/'  # get_root_storage_path_on_hpc() + 'Data/emissions/CAMS-GFAS/
# INPUT_NAME = 'ga_<date>.grb'
# OUTPUT_PATH = INPUT_PATH + '/hermesv3_gr_pp/'
# PARAMETERS_FILE = '/work/mm0062/b302074/workspace/python/hermesv3_gr/preproc/GFAS_Parameters.csv'

# Shaheen
# INPUT_PATH = '/project/k10048/osipovs/Data/emissions/CAMS-GFAS/'
# INPUT_NAME = 'ga_<date>.grb'
# OUTPUT_PATH = '/scratch/osipovs/bandwidth/Data/emissions/CAMS-GFAS/' + '/hermesv3_gr_pp/'  # put on bandwidth for faster IO
# PARAMETERS_FILE = '/scratch/osipovs/iops/sw/workspace/hermesv3_gr/preproc/GFAS_Parameters.csv'

# STARTING_DATE = datetime(year=2021, month=1, day=1)
# ENDIND_DATE = datetime(year=2022, month=1, day=1)
# ==============================================================


def write_netcdf(output_name_path, data_list, center_lats, center_lons, grid_cell_area, date):
    """
    Write a NetCDF with the given information.

    :param output_name_path: Complete path to the output NetCDF to be stored.
    :type output_name_path: str

    :param data_list

    :param center_lats: Latitudes of the center of each cell.
    :type center_lats: numpy.array

    :param center_lons: Longitudes of the center of each cell.
    :type center_lons: numpy.array

    :param grid_cell_area: Area of each cell of the grid.
    :type grid_cell_area: numpy.array

    :param date: Date of the current netCDF.
    :type date: datetime.datetime

    """
    print(output_name_path)
    # Creating NetCDF & Dimensions
    nc_output = Dataset(output_name_path, mode='w', format="NETCDF4")
    nc_output.createDimension('nv', 2)
    nc_output.createDimension('lon', center_lons.shape[0])
    nc_output.createDimension('lat', center_lats.shape[0])
    nc_output.createDimension('time', None)

    # TIME
    time = nc_output.createVariable('time', 'd', ('time',), zlib=True)
    # time.units = "{0} since {1}".format(tstep_units, global_atts['Start_DateTime'].strftime('%Y-%m-%d %H:%M:%S'))
    time.units = "hours since {0}".format(date.strftime('%Y-%m-%d %H:%M:%S'))
    time.standard_name = "time"
    time.calendar = "gregorian"
    time.long_name = "time"
    time[:] = [0]

    # LATITUDE
    lat = nc_output.createVariable('lat', 'f', ('lat',), zlib=True)
    lat.bounds = "lat_bnds"
    lat.units = "degrees_north"
    lat.axis = "Y"
    lat.long_name = "latitude"
    lat.standard_name = "latitude"
    lat[:] = center_lats

    lat_bnds = nc_output.createVariable('lat_bnds', 'f', ('lat', 'nv',), zlib=True)
    lat_bnds[:] = create_bounds(center_lats)

    # LONGITUDE
    lon = nc_output.createVariable('lon', 'f', ('lon',), zlib=True)
    lon.bounds = "lon_bnds"
    lon.units = "degrees_east"
    lon.axis = "X"
    lon.long_name = "longitude"
    lon.standard_name = "longitude"
    lon[:] = center_lons

    lon_bnds = nc_output.createVariable('lon_bnds', 'f', ('lon', 'nv',), zlib=True)
    lon_bnds[:] = create_bounds(center_lons)

    for var in data_list:
        # VARIABLE
        nc_var = nc_output.createVariable(var['name'], 'f', ('time', 'lat', 'lon',), zlib=True)
        nc_var.units = var['units'].symbol
        nc_var.long_name = var['long_name']
        nc_var.coordinates = 'lat lon'
        nc_var.grid_mapping = 'crs'
        nc_var.cell_measures = 'area: cell_area'
        nc_var[:] = var['data']

    # CELL AREA
    cell_area = nc_output.createVariable('cell_area', 'f', ('lat', 'lon',))
    cell_area.long_name = "area of the grid cell"
    cell_area.standard_name = "area"
    cell_area.units = "m2"
    cell_area[:] = grid_cell_area

    # CRS
    crs = nc_output.createVariable('crs', 'i')
    crs.grid_mapping_name = "latitude_longitude"
    crs.semi_major_axis = 6371000.0
    crs.inverse_flattening = 0

    nc_output.setncattr('title', 'GFASv1.2 inventory')
    nc_output.setncattr('Conventions', 'CF-1.6', )
    nc_output.setncattr('institution', 'ECMWF', )
    nc_output.setncattr('source', 'GFAS', )

    nc_output.close()
    return True


def do_transformation(input_file, date, output_dir, variables_list):
    """
    Transform the original file into a NEtCDF file that follows the conventions.

    :param input_file:
    :type input_file: str

    :param date: Date of the file to do the transformation.
    :type date: datetime.datetime

    :param output_dir: Path where have to be stored the output file.
    :type output_dir: str

    :param variables_list: LIst of dictionaries with the information of each variable of the output files.
    :type variables_list: list
    """
    from cdo import Cdo
    cdo = Cdo()
    # lets see if this fixes the "file not found" bug
    #cdo = Cdo(tempdir='/scratch/b/b302074/')

    nc_temp = cdo.copy(input=input_file, options='-R -r -f nc4c -z zip_4')
    #nc_temp = '/scratch/b/b302074/cdo_temp'  # fix the "file not found" bug
    #cdo.copy(input=input_file, options='-R -r -f nc4c -z zip_4', output=nc_temp)

    nc_in = Dataset(nc_temp, mode='r')

    cell_area = get_grid_area(nc_temp)

    lats = nc_in.variables['lat'][:]
    lons = nc_in.variables['lon'][:]

    for variable in variables_list:
        variable['data'] = nc_in.variables[variable['original_name']][:]

    nc_in.close()

    out_path_aux = os.path.join(output_dir, 'daily_mean', 'multivar')
    if not os.path.exists(out_path_aux):
        os.makedirs(out_path_aux)
    out_path_aux = os.path.join(out_path_aux, 'ga_{0}.nc'.format(date.strftime('%Y%m%d')))
    write_netcdf(out_path_aux, variables_list, lats, lons, cell_area, date)

    return True


def do_var_list(variables_file):
    """
    Create the List of dictionaries

    :param variables_file: CSV file with the information of each variable
    :type variables_file: str

    :return: Dictionaries list with the information of each variable.
    :rtype: list
    """
    df = pd.read_csv(variables_file, sep=';')
    list_aux = []
    for i, element in df.iterrows():
        # print element
        dict_aux = {
            'original_name': 'var' + str(element.id),
            'name': element['Short_Name'],
            'long_name': element['Name'],
            'units': cf_units.Unit(element['Units']),
        }
        list_aux.append(dict_aux)
    return list_aux


if __name__ == '__main__':
    var_list = do_var_list(args.parameters_file)

    if args.in_file_path:
        match = re.search(r'_(\d{8})\.', args.in_file_path)
        date_string = match.group(1)
        date_aux = datetime.strptime(date_string, '%Y%m%d').date()
        do_transformation(args.in_file_path, date_aux, args.output_folder_path, [dict(v) for v in var_list])
    else:
        for ts in pd.date_range(start=args.start_date, end=args.end_date, freq='D'):
            date_compact = ts.strftime('%Y%m%d')
            out_file = os.path.join(args.output_folder_path, 'daily_mean', 'multivar', 'ga_{0}.nc'.format(date_compact))
            if not args.overwrite and os.path.isfile(out_file) and os.path.getsize(out_file) > 0:
                print('Skipping existing output: {0}'.format(out_file))
                continue
            in_file = os.path.join(args.input_dir, 'ga_{0}.grb'.format(date_compact))
            if not os.path.isfile(in_file):
                raise FileNotFoundError('Expected CAMS-GFAS GRIB file not found: {0}'.format(in_file))
            do_transformation(in_file, ts.date(), args.output_folder_path, [dict(v) for v in var_list])
