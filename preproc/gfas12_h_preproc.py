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
import cf_units
import pandas as pd
import datetime
from datetime import datetime, timedelta

from hermesv3_gr.tools.coordinates_tools import create_bounds

# ============== README ======================
"""
downloading website: http://apps.ecmwf.int/datasets/data/cams-gfas/
reference: https://www.biogeosciences.net/9/527/2012/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/ecmwf/gfas/original_files/ga_mc_sfc_gfas_ecmf/'
INPUT_NAME = 'gfas_hourly_<date>.grb'
OUTPUT_PATH = '/esarchive/recon/ecmwf/gfas'

STARTING_DATE = datetime(year=2018, month=11, day=0o1)
ENDIND_DATE = datetime(year=2018, month=11, day=0o1)

PARAMETERS_FILE = '/esarchive/recon/ecmwf/gfas/original_files/ga_mc_sfc_gfas_ecmf/GFAS_hourly_Parameters.csv'
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
    nc_output.setncattr('history', 'Re-writing of the GFAS input to follow the CF-1.6 conventions;\n' +
                        '2019-01-02: Added boundaries;\n' +
                        '2019-01-02: Added global attributes;\n' +
                        '2019-01-02: Re-naming pollutant;\n' +
                        '2019-01-02: Added cell_area variable;\n' +
                        '2019-01-02: Added new varaibles;\n')
    nc_output.setncattr('references', 'downloading website: http://apps.ecmwf.int/datasets/data/cams-gfas/\n' +
                        'reference: https://www.biogeosciences.net/9/527/2012/', )
    nc_output.setncattr('comment', 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                        '(Barcelona Supercomputing Center)', )

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

    nc_temp = cdo.copy(input=input_file, options='-R -r -f nc4c -z zip_4')

    nc_in = Dataset(nc_temp, mode='r')

    cell_area = get_grid_area(nc_temp)

    lats = nc_in.variables['lat'][:]
    lons = nc_in.variables['lon'][:]

    for variable in variables_list:
        variable['data'] = nc_in.variables[variable['original_name']][:]

    nc_in.close()

    out_path_aux = os.path.join(output_dir, '1hourly', 'multivar')
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
            'original_name': str(element.id),
            'name': element['Short_Name'],
            'long_name': element['Name'],
            'units': cf_units.Unit(element['Units']),
        }
        list_aux.append(dict_aux)
    return list_aux


if __name__ == '__main__':

    var_list = do_var_list(PARAMETERS_FILE)

    date_aux = STARTING_DATE
    while date_aux <= ENDIND_DATE:
        f = os.path.join(INPUT_PATH, INPUT_NAME.replace('<date>', date_aux.strftime('%Y%m%d')))
        if os.path.isfile(f):
            do_transformation(f, date_aux, OUTPUT_PATH, var_list)
        else:
            print('ERROR: file {0} not found'.format(f))

        date_aux = date_aux + timedelta(days=1)
