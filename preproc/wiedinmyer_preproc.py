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
import timeit
from netCDF4 import Dataset

# ============== README ======================
"""
downloading website: http://bai.acom.ucar.edu/Data/fire/
reference: https://pubs.acs.org/doi/abs/10.1021/es502250z
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = os.environ.get('WIEDINMYER_INPUT_PATH', '/HDD1/Data/emissions/ucar/wiedinmyer/original_files')
OUTPUT_PATH = os.environ.get('WIEDINMYER_OUTPUT_PATH', '/HDD1/Data/emissions/ucar/wiedinmyer')

LIST_POLLUTANTS = ['co2', 'co', 'so2', 'nox_no', 'nh3', 'ch4', 'c2h2', 'c2h4', 'c3h6', 'ch3oh', 'ch2o', 'ch3cooh',
                   'hcn', 'c6h6', 'pcb', 'pah', 'pcdd', 'pbdd', 'nmoc', 'hcl', 'hg', 'pm25', 'pm10', 'oc', 'bc']

INPUT_NAME = 'ALL_Emiss_04282014.nc'
YEAR = 2010
# ==============================================================


def out_pollutant_to_in_pollutant(out_p):
    # TODO Documentation
    pollutant_dict = {
        'co2': 'CO2grid',
        'co': 'COgrid',
        'so2': 'SO2grid',
        'nox_no': 'NOxgrid',
        'nh3': 'NH3grid',
        'ch4': 'CH4grid',
        'c2h2': 'C2H2grid',
        'c2h4': 'C2H4grid',
        'c3h6': 'C3H6grid',
        'ch3oh': 'MEOHgrid',
        'ch2o': 'FORMgrid',
        'ch3cooh': 'AcetAcidgrid',
        'hcn': 'HCNgrid',
        'c6h6': 'BENZgrid',
        'pcb': 'PCBgrid',
        'pah': 'PAHgrid',
        'pcdd': 'PCDDgrid',
        'pbdd': 'PBDDgrid',
        'nmoc': 'NMOCgrid',
        'hcl': 'HClgrid',
        'hg': 'Hggrid',
        'pm25': 'PM25grid',
        'pm10': 'PM10grid',
        'oc': 'OCgrid',
        'bc': 'BCgrid',
    }

    return pollutant_dict[out_p]


def do_transformation(filename):
    """
    Re-write the WIEDINMYER inputs following ES anc CF-1.6 conventions.

    :param filename: Name of the input file.
    :type filename: str
    """
    import numpy as np
    print(filename)
    from hermesv3_gr.tools.netcdf_tools import get_grid_area
    from cf_units import Unit

    grid_area = get_grid_area(filename)

    nc_in = Dataset(filename, mode='r')

    # Reading lat, lon
    # lats = nc_in.variables['lat'][:]
    # lons = nc_in.variables['lon'][:]

    lats = np.arange(89.95, -90, -0.1, dtype=np.float64)
    lons = np.arange(-179.95, 180, 0.1, dtype=np.float64)

    factor = 1000000./(365.*24.*3600.)  # To pass from Gg/m2.year to Kg/m2.s

    for output_pollutant in LIST_POLLUTANTS:
        input_pollutant = out_pollutant_to_in_pollutant(output_pollutant)
        try:
            print(input_pollutant)
            data = nc_in.variables[input_pollutant][:]
        except RuntimeWarning:
            print('ERROR reading {0}'.format(input_pollutant))
        data = np.nan_to_num(data)
        data = data/grid_area  # To pass from Gg/year to Gg/m2.year
        data = data*factor
        data_attributes = {'name': output_pollutant,
                           'long_name': nc_in.variables[input_pollutant].long_name,
                           'units': Unit('kg.m-2.s-1').symbol,
                           'coordiantes': 'lat lon',
                           'grid_mapping': 'crs'}
        data = np.array(data)

        out_path_aux = os.path.join(OUTPUT_PATH, 'yearly_mean', output_pollutant)
        if not os.path.exists(out_path_aux):
            os.makedirs(out_path_aux)
        write_netcdf(os.path.join(out_path_aux, '{0}_{1}.nc'.format(output_pollutant, YEAR)),
                     data, data_attributes, lats, lons, grid_area, YEAR, 0o1)
    nc_in.close()


def write_netcdf(output_name_path, data, data_atts, center_lats, center_lons, grid_cell_area, time_year, time_month):
    """
    Write a NetCDF with the given information.

    :param output_name_path: Complete path to the output NetCDF to be stored.
    :type output_name_path: str

    :param data: Data of the variable to be stored.
    :type data: numpy.array

    :param data_atts: Information of the data to fill the data attributes of the NetCDF variable.
        'long_name': Name of the pollutant.
        'units': Units of the pollutant.
        'coordiantes': Variables that contains the coordinates of the data.
        'grid_mapping': Mapping variable
    :type data_atts: dict

    :param center_lats: Latitudes of the center of each cell.
    :type center_lats: numpy.array

    :param center_lons: Longitudes of the center of each cell.
    :type center_lons: numpy.array

    :param grid_cell_area: Area of each cell of the grid.
    :type: numpy.array

    :param time_year: Year.
    :type time_year: int

    :param time_month: Number of the month.
    :type time_month: int
    """
    from hermesv3_gr.tools.coordinates_tools import create_bounds

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
    time.units = "months since {0}-{1}-01 00:00:00".format(time_year, str(time_month).zfill(2))
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

    # VARIABLE
    nc_var = nc_output.createVariable(data_atts['name'], 'f', ('time', 'lat', 'lon',), zlib=True)
    nc_var.units = data_atts['units']
    nc_var.long_name = data_atts['long_name']
    nc_var.coordinates = data_atts['coordiantes']
    nc_var.grid_mapping = data_atts['grid_mapping']
    nc_var.cell_measures = 'area: cell_area'
    nc_var[:] = data.reshape((1,) + data.shape)

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

    nc_output.setncattr('title', 'Annual trash burning emissions', )
    nc_output.setncattr('Conventions', 'CF-1.6', )
    nc_output.setncattr('institution', 'UCAR', )
    nc_output.setncattr('source', 'WIEDINMYER', )
    nc_output.setncattr('history', 'Re-writing of the WIEDINMYER input to follow the CF 1.6 conventions;\n' +
                        '2014-04-28: Created by C. Wiedinmyer;\n' +
                        '2017-04-04: Added time dimension (UNLIMITED);\n' +
                        '2017-04-04: Added boundaries;\n' +
                        '2017-04-04: Added global attributes;\n' +
                        '2017-04-04: Re-naming pollutant;\n' +
                        '2017-04-04: Added cell_area variable;\n')
    nc_output.setncattr('references', '', )
    nc_output.setncattr('comment', 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                        '(Barcelona Supercomputing Center); Original file from C. Wiedinmyer', )

    nc_output.close()


if __name__ == '__main__':
    starting_time = timeit.default_timer()

    do_transformation(os.path.join(INPUT_PATH, INPUT_NAME))

    print('Time(s):', timeit.default_timer() - starting_time)
