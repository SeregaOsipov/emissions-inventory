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
import sys
import numpy as np

# ============== README ======================
"""
downloading website: 
reference: 
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/ecmwf/cams81/original_files/cams_glob_ship/2015'
OUTPUT_PATH = '/esarchive/recon/ecmwf/cams_glob_shipv11'
LIST_POLLUTANTS = ['NOx', 'SOx', 'EC', 'OC', 'SO4', 'CO', 'CO2', 'VOC_SUM', 'Ash']
# LIST_POLLUTANTS = ['VOC_SUM']
# LIST_YEARS = from 2000 to 2015
LIST_YEARS = [2015]
INPUT_NAME = 'CAMS-GLOB-SHIP_GlbP_0.25x0.25_anthro_<pollutant>_v1.1_monthly.nc'
# ==============================================================


def get_full_year_data(file_name, year):
    """
    Gets the needed date in the input format.

    :param file_name: path to the input file.
    :type file_name: str

    :param pollutant: Name of the pollutant.
    :type pollutant: str

    :param sector: Name of the sector.
    :type sector: str

    :param year: Year to calculate.
    :type year: int

    :return: Data of the selected emission.
    :rtype: numpy.array
    """
    from netCDF4 import Dataset
    from datetime import datetime
    import cf_units
    import numpy as np

    nc = Dataset(file_name, mode='r')

    time = nc.variables['time']

    time_array = cf_units.num2date(time[:], time.units, time.calendar)
    time_array = np.array([datetime(year=x.year, month=x.month, day=1) for x in time_array])

    i_time = np.where(time_array == datetime(year=year, month=1, day=1))[0][0]

    # if sector in LIST_SECTORS:
    data = nc.variables['sum'][i_time:i_time+12, :, :]
    # else:
    #     data = None
    nc.close()

    return data


def get_global_attributes(file_name):
    """
    Gets the global attributes of the input file.

    :param file_name: Path to the NetCDF file
    :type file_name: str

    :return: Global attributes
    :rtype: dict
    """
    from netCDF4 import Dataset

    nc = Dataset(file_name, mode='r')

    atts_dict = {}
    for name in nc.ncattrs():
        atts_dict[name] = nc.getncattr(name)

    nc.close()
    return atts_dict

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


def do_transformation(year):
    """
    Does the transformation for the selected year

    :param year: Year to calculate
    :type year: int
    """
    from datetime import datetime
    from hermesv3_gr.tools.netcdf_tools import extract_vars, get_grid_area, write_netcdf
    for pollutant in LIST_POLLUTANTS:
        file_name = get_input_name(pollutant)
        if os.path.exists(file_name):
            # c_lats, c_lons, b_lats, b_lons = extract_vars(file_name, ['lat', 'lon', 'lat_bnds', 'lon_bnds'])
            c_lats, c_lons = extract_vars(file_name, ['lat', 'lon'])

            b_lats = create_bounds(c_lats['data'])
            b_lons = create_bounds(c_lons['data'])

            # cell_area = get_grid_area(file_name)

            global_attributes = get_global_attributes(file_name)

            data = get_full_year_data(file_name, year)

            if pollutant == 'NOx':
                pollutant_name = 'nox_no'

            elif pollutant == 'VOC_SUM':
                pollutant_name = 'nmvoc'

            elif pollutant == 'SOx':
                pollutant_name = 'so2'

            else:
                pollutant_name = pollutant.lower()

            file_path = os.path.join(OUTPUT_PATH, 'monthly_mean', '{0}'.format(pollutant_name))
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            for month in range(1, 12 + 1, 1):
                emission = {
                    'name': pollutant_name,
                    'units': 'kg.m-2.s-1',
                    # 'data': data[month - 1, :, :].reshape((1,) + cell_area.shape)
                    'data': data[month - 1, :, :].reshape((1, data.shape[-2], data.shape[-1]))

                }
                # write_netcdf(
                #     os.path.join(file_path, '{0}_{1}{2}.nc'.format(pollutant_name, year, str(month).zfill(2))),
                #     c_lats['data'], c_lons['data'], [emission], date=datetime(year=year, month=month, day=1),
                #     boundary_latitudes=b_lats, boundary_longitudes=b_lons, cell_area=cell_area,
                #     global_attributes=global_attributes)

                write_netcdf(
                    os.path.join(file_path, '{0}_{1}{2}.nc'.format(pollutant_name, year, str(month).zfill(2))),
                    c_lats['data'], c_lons['data'], [emission], date=datetime(year=year, month=month, day=1),
                    boundary_latitudes=b_lats, boundary_longitudes=b_lons, global_attributes=global_attributes)
        else:
            raise IOError('File not found {0}'.format(file_name))
    return True



if __name__ == '__main__':
    for y in LIST_YEARS:
        do_transformation(y)