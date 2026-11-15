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
from datetime import datetime
from netCDF4 import Dataset
import numpy as np
from cf_units import Unit

# ============== README ======================
"""
downloading website: http://www.iiasa.ac.at/web/home/research/researchPrograms/air/ECLIPSEv5a.html
reference: http://pure.iiasa.ac.at/id/eprint/11367/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/iiasa/eclipsev5a/original_files'
OUTPUT_PATH = '/esarchive/recon/iiasa/eclipsev5a'
INPUT_NAME = 'ECLIPSE_base_CLE_V5a_<pollutant>.nc'
INPUT_NAME_FLARING = 'ECLIPSE_V5a_baseline_CLE_flaring.nc'
INPUT_NAME_SHIPS = "ship_CLE_emis_<year>.nc"
MONTHLY_PATTERN_FILE = 'ECLIPSEv5_monthly_patterns.nc'
LIST_YEARS = [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030, 2040, 2050]
LIST_POLLUTANTS = ['BC', 'CH4', 'CO', 'NH3', 'NOx', 'OC', 'OM', 'PM10', 'PM25', 'SO2', 'VOC']
# ==============================================================


MONTH_FACTOR = 1000000. / (30. * 24. * 3600.)  # To pass from kt/month to Kg/s
YEAR_FACTOR = 1000000. / (365. * 24. * 3600.)  # To pass from kt/year to Kg/s
VAR_UNITS = 'kg.m-2.s-1'


def get_grid_area(filename):
    """
    Calculate the area for each cell of the grid using CDO

    :param filename: Path to the file to calculate the cell area
    :type filename: str

    :return: Area of each cell of the grid.
    :rtype: numpy.array
    """
    from cdo import Cdo

    cdo = Cdo()
    src = cdo.gridarea(input=filename)
    nc_aux = Dataset(src, mode='r')
    grid_area = nc_aux.variables['cell_area'][:]
    nc_aux.close()

    return grid_area


def create_bounds(coordinates, number_vertices=2):
    """
    Calculate the vertices coordinates.

    :param coordinates: Coordinates in degrees (latitude or longitude)
    :type coordinates: numpy.array

    :param number_vertices: Non mandatory parameter that informs the number of vertices that must have the boundaries.
            (by default 2)
    :type number_vertices: int

    :return: Array with as many elements as vertices for each value of coords.
    :rtype: numpy.array
    """
    interval = coordinates[1] - coordinates[0]

    coords_left = coordinates - interval / 2
    coords_right = coordinates + interval / 2
    if number_vertices == 2:
        bound_coords = np.dstack((coords_left, coords_right))
    elif number_vertices == 4:
        bound_coords = np.dstack((coords_left, coords_right, coords_right, coords_left))
    else:
        raise ValueError('The number of vertices of the boudaries must be 2 or 4')

    return bound_coords


def write_netcdf(output_name_path, data_list, center_lats, center_lons, grid_cell_area, date):
    # TODO Documentation
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

    nc_output.setncattr('title', 'ECLIPSEv5a inventory')
    nc_output.setncattr('Conventions', 'CF-1.6', )
    nc_output.setncattr('institution', 'IIASA', )
    nc_output.setncattr('source', 'IIASA', )
    nc_output.setncattr('history', 'Re-writing of the ECLIPSEv5a input to follow the CF-1.6 conventions;\n' +
                        '2017-11-28: Creating;\n')
    nc_output.setncattr('web', 'http://www.iiasa.ac.at/web/home/research/researchPrograms/air/ECLIPSEv5a.html')
    nc_output.setncattr('comment', 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                        '(Barcelona Supercomputing Center)', )

    nc_output.close()


def extract_sector_by_name(name):
    # TODO Documentation
    sector_dict = {
        'emis_agr': 'agriculture',
        'emis_awb': 'agriculture_waste',
        'emis_dom': 'residential',
        'emis_ene': 'energy',
        'emis_ind': 'industry',
        'emis_tra': 'transport',
        'emis_wst': 'waste',
        'emis_slv': 'solvent',
    }

    try:
        return_value = sector_dict[name]
    except KeyError:
        return_value = None

    return return_value


def extract_month_profile_by_sector(sector, month, pollutant=None):
    # TODO Documentation
    sector_dict = {
        'residential': 'dom',
        'energy': 'ene',
        'agriculture_waste': 'agr_awb',
        'agriculture': 'agr',
        'industry': 'ind',
        'transport': 'tra',
        'waste': 'other',
        'solvent': 'other',
    }
    if sector == '' and pollutant == 'NH3':
        profile_name = 'agr_NH3'
    else:
        profile_name = sector_dict[sector]

    nc_profiles = Dataset(os.path.join(INPUT_PATH, MONTHLY_PATTERN_FILE), mode='r')

    profile = nc_profiles.variables[profile_name][month, :, :]

    nc_profiles.close()
    profile = np.nan_to_num(profile)
    # profile = profile.nan_to_num()
    return profile


def get_output_name(pollutant, sector, year, month):
    # TODO Docuemtnation
    output_path_aux = os.path.join(OUTPUT_PATH, 'monthly_mean', '{0}_{1}'.format(pollutant, sector), )

    if not(os.path.exists(output_path_aux)):
        os.makedirs(output_path_aux)
    return os.path.join(output_path_aux, '{0}_{1}.nc'.format(
        pollutant, datetime(year=year, month=month, day=1).strftime('%Y%m')))


def do_single_transformation(pollutant, sector, data, c_lats, c_lons, cell_area):
    # TODO Docuemtnation
    for i in range(len(LIST_YEARS)):

        for month in range(12):
            # print i, list_years[i], month + 1
            if pollutant == 'NOx':
                pollutant_name = 'nox_no2'
            elif pollutant == 'VOC':
                pollutant_name = 'nmvoc'
            else:
                pollutant_name = pollutant.lower()
            output_name = get_output_name(pollutant_name.lower(), sector.lower(), LIST_YEARS[i], month + 1)
            profile = extract_month_profile_by_sector(sector, month, pollutant)
            data_aux = data[i, :, :] * profile
            # print factor
            data_aux = (data_aux * MONTH_FACTOR) / cell_area
            # #data_aux = data_aux / cell_area
            # print 'original: ', data[i, 192, 404]
            # print 'factor: ', profile[192, 404]
            # print 'destiny', data_aux[192, 404]
            data_aux = data_aux.reshape((1,) + data_aux.shape)
            data_list = [{
                'name': pollutant_name,
                'long_name': pollutant_name,
                'data': data_aux,
                'units': Unit(VAR_UNITS),
            }]
            write_netcdf(output_name, data_list, c_lats, c_lons, cell_area,
                         datetime(year=LIST_YEARS[i], month=month + 1, day=1))


def do_transformation():
    # TODO Documentation
    for pollutant in LIST_POLLUTANTS:
        file_name = os.path.join(INPUT_PATH, INPUT_NAME.replace('<pollutant>', pollutant))
        print(file_name)
        nc = Dataset(file_name, mode='r')
        c_lats = nc.variables['lat'][:]
        c_lons = nc.variables['lon'][:]
        cell_area = get_grid_area(file_name)
        for var in nc.variables:
            sector = extract_sector_by_name(var)

            if sector is not None:
                do_single_transformation(pollutant, sector, nc.variables[var][:], c_lats, c_lons, cell_area)
        nc.close()


def get_flaring_output_name(pollutant, sector, year):
    # TODO Docuemtnation
    output_path_aux = os.path.join(OUTPUT_PATH, 'yearly_mean', '{0}_{1}'.format(pollutant, sector), )

    if not(os.path.exists(output_path_aux)):
        os.makedirs(output_path_aux)
    return os.path.join(output_path_aux, '{0}_{1}.nc'.format(pollutant,
                                                             datetime(year=year, month=1, day=1).strftime('%Y')))


def get_flaring_var_name(nc_var):
    # TODO Docuemtnation
    nc_var_2_var = {
        'emis_SO2_flr': 'so2',
        'emis_NOx_flr': 'nox_no2',
        'emis_NH3_flr': 'nh3',
        'emis_VOC_flr': 'nmvoc',
        'emis_PM25_flr': 'pm25',
        'emis_BC_flr': 'bc',
        'emis_OC_flr': 'oc',
        'emis_PM10_flr': 'pm10',
        'emis_CO_flr': 'co',
        'emis_CH4_flr': 'ch4',
    }
    try:
        return_value = nc_var_2_var[nc_var]
    except KeyError:
        return_value = None
    return return_value


def do_flaring_transformation():
    # TODO Documentation
    nc_in = Dataset(os.path.join(INPUT_PATH, INPUT_NAME_FLARING), mode='r')
    c_lats = nc_in.variables['lat'][:]
    c_lons = nc_in.variables['lon'][:]
    cell_area = get_grid_area(os.path.join(INPUT_PATH, INPUT_NAME_FLARING))
    for var in nc_in.variables:
        var_name = get_flaring_var_name(var)
        if var_name is not None:
            data = nc_in.variables[var][:]
            data = np.nan_to_num(data)
            for i in range(len(LIST_YEARS)):
                output_name = get_flaring_output_name(var_name, 'flaring', LIST_YEARS[i])
                data_aux = data[i, :, :]
                data_aux = (data_aux * YEAR_FACTOR) / cell_area
                data_aux = data_aux.reshape((1,) + data_aux.shape)
                data_list = [{
                    'name': var_name,
                    'long_name': var_name,
                    'data': data_aux,
                    'units': Unit(VAR_UNITS),
                }]
                write_netcdf(output_name, data_list, c_lats, c_lons, cell_area,
                             datetime(year=LIST_YEARS[i], month=1, day=1))
    nc_in.close()


def get_ship_output_name(pollutant, sector, year):
    # TODO Docuemntation
    output_path_aux = os.path.join(OUTPUT_PATH, 'yearly_mean', '{0}_{1}'.format(pollutant, sector), )

    if not(os.path.exists(output_path_aux)):
        os.makedirs(output_path_aux)
    return os.path.join(output_path_aux, '{0}_{1}.nc'.format(pollutant,
                                                             datetime(year=year, month=1, day=1).strftime('%Y')))


def get_ship_var_name(nc_var):
    # TODO Documentation
    nc_var_2_var = {
        'SO2': 'so2',
        'NOx': 'nox_no2',
        'VOC': 'nmvoc',
        'PM25': 'pm25',
        'BC': 'bc',
        'OC': 'oc',
        'PM10': 'pm10',
        'CO': 'co',
        'CH4': 'ch4',
    }
    try:
        return_value = nc_var_2_var[nc_var]
    except KeyError:
        return_value = None
    return return_value


def do_ship_transformation():
    # TODO Documentation
    for year in LIST_YEARS:
        in_path = os.path.join(INPUT_PATH, INPUT_NAME_SHIPS.replace('<year>', str(year)))
        nc_in = Dataset(in_path, mode='r')
        c_lats = nc_in.variables['lat'][:]
        c_lons = nc_in.variables['lon'][:]

        cell_area = get_grid_area(in_path)

        for var in nc_in.variables:
            var_name = get_ship_var_name(var)
            if var_name is not None:
                data = nc_in.variables[var][0, :, :]
                data = np.nan_to_num(data)

                data = (data * YEAR_FACTOR) / cell_area
                data = data.reshape((1,) + data.shape)
                data_list = [{
                    'name': var_name,
                    'long_name': var_name,
                    'data': data,
                    'units': Unit(VAR_UNITS),
                }]

                write_netcdf(get_ship_output_name(var_name, 'ship', year), data_list, c_lats, c_lons, cell_area,
                             datetime(year=year, month=1, day=1))
        nc_in.close()


if __name__ == '__main__':
    do_transformation()
    do_flaring_transformation()
    do_ship_transformation()
