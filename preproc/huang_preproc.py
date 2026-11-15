#!/usr/bin/env python

import os
import sys
import numpy as np

"""
Flaring BC emissions from Huang et al., 
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/work/mm0062/b302074/Data/emissions/huangetal/original_files'
OUTPUT_PATH = INPUT_PATH + '/../'
LIST_POLLUTANTS = ['flare',]  # flare == bc
LIST_YEARS = [2012]
INPUT_NAME = 'flare_BC_emis_1994-2012.nc'
# ==============================================================


def get_yearly_data(file_name, pollutant, year):
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
    import netCDF4

    nc = Dataset(file_name, mode='r')

    years = nc.variables['time'][:]
    time_index = np.where(years==year)[0][0]
    data = nc.variables[pollutant][time_index]

    nc.close()

    return data, years[time_index]


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

            cell_area = get_grid_area(file_name)

            global_attributes = get_global_attributes(file_name)

            data, yearly_dates = get_yearly_data(file_name, pollutant, year)

            pollutant_name = 'bc'  # pollutant.lower()

            file_path = os.path.join(OUTPUT_PATH, 'yearly_mean', '{0}'.format(pollutant_name))
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            emission = {
                'name': pollutant_name,
                'units': 'kg.m-2.s-1',
                'data': data.reshape((1, data.shape[-2], data.shape[-1]))
            }

            date = datetime(year, 1, 1)

            write_netcdf(
                os.path.join(file_path, '{0}_{1}.nc'.format(pollutant_name, year)),
                c_lats['data'], c_lons['data'], [emission], date=date,
                boundary_latitudes=b_lats, boundary_longitudes=b_lons, global_attributes=global_attributes,
                cell_area=cell_area)
        else:
            raise IOError('File not found {0}'.format(file_name))
    return True


if __name__ == '__main__':
    for y in LIST_YEARS:
        do_transformation(y)