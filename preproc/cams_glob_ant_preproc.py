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
INPUT_PATH = '/esarchive/recon/ecmwf/cams81/original_files/cams_glob_ant'
OUTPUT_PATH = '/esarchive/recon/ecmwf/cams_glob_antv21'
LIST_POLLUTANTS = ['bc', 'co', 'nh3', 'nmvoc', 'nox', 'oc', 'so2', 'co2', 'ch4', 'voc1', 'voc2', 'voc3', 'voc4', 'voc5', 'voc6', 'voc7', 'voc8', 'voc9', 'voc12', 'voc13',
                  'voc14', 'voc15', 'voc16', 'voc17', 'voc18', 'voc19', 'voc20', 'voc21', 'voc22', 'voc23', 'voc24',
                  'voc25']
#LIST_POLLUTANTS = ['voc1', 'voc2', 'voc3', 'voc4', 'voc5', 'voc6', 'voc7', 'voc8', 'voc9']

# VOC_POLLUTANTS = ['voc1', 'voc2', 'voc3', 'voc4', 'voc5', 'voc6', 'voc7', 'voc8', 'voc9', 'voc12', 'voc13',
#                   'voc14', 'voc15', 'voc16', 'voc17', 'voc18', 'voc19', 'voc20', 'voc21', 'voc22', 'voc23', 'voc24',
#                   'voc25']

LIST_SECTORS = ['agriculture', 'energy', 'industry', 'road_transport', 'residential', 'solvents', 'waste', 'shipping', 'livestock',
                'fugitive_fuel', 'non_road_transport']
# LIST_YEARS = from 1950 to 2014
LIST_YEARS = [2015]
INPUT_NAME = 'CAMS-GLOB-ANT_Glb_0.1x0.1_anthro_<pollutant>_v2.1.nc'
# VOC_INPUT_NAME = '<voc_name>-em-speciated-VOC_input4MIPs_emissions_CMIP_CEDS-v2016-07-26-sector' + \
#                  'Dim-supplemental-data_gr_<st_year>01-<en_year>12.nc'
# DO_AIR = True
# AIR_INPUT_NAME = '<pollutant>-em-AIR-anthro_input4MIPs_emissions_CMIP_CEDS-v2016-07-26_gr_<st_year>01-<en_year>12.nc'
# ==============================================================


def sector_to_index(sector):
    """
    Gets the index where are allocated the emissions for the selected sector.

    :param sector: Name to the sector to get the index position.
    :type sector: str

    :return: Index of the position of the current sector
    :rtype: int
    """
    sector_dict = {
        'agriculture': 'agr',
        'energy': 'ene',
        'industry': 'ind',
        'road_transport': 'tro',
        'residential': 'res',
        'solvents': 'slv',
        'waste': 'swd',
        'shipping': 'shp',
        'livestock': 'mma',
        'fugitive_fuel': 'fef',
        'non_road_transport': 'tnr'
    }

    return sector_dict[sector]


def get_full_year_data(file_name, sector, year):
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

    if sector in LIST_SECTORS:
        data = nc.variables['{0}'.format(sector_to_index(sector))][i_time:i_time+12, :, :]
    else:
        data = None
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
            for sector in LIST_SECTORS:
                data = get_full_year_data(file_name, sector, year)

                if pollutant == 'nox':
                    pollutant_name = 'nox_no'
                elif pollutant == 'voc1':
                    pollutant_name = 'voc01'
                elif pollutant == 'voc2':
                    pollutant_name = 'voc02'
                elif pollutant == 'voc3':
                    pollutant_name = 'voc03'
                elif pollutant == 'voc4':
                    pollutant_name = 'voc04'
                elif pollutant == 'voc5':
                    pollutant_name = 'voc05'
                elif pollutant == 'voc6':
                    pollutant_name = 'voc06'
                elif pollutant == 'voc7':
                    pollutant_name = 'voc07'
                elif pollutant == 'voc8':
                    pollutant_name = 'voc08'
                elif pollutant == 'voc9':
                    pollutant_name = 'voc09'
                else:
                    pollutant_name = pollutant

                file_path = os.path.join(OUTPUT_PATH, 'monthly_mean', '{0}_{1}'.format(pollutant_name, sector))
                if not os.path.exists(file_path):
                    os.makedirs(file_path)

                for month in range(1, 12 + 1, 1):
                    emission = {
                        'name': pollutant_name,
                        'units': 'kg.m-2.s-1',
                        'data': data[month - 1, :, :].reshape((1,) + cell_area.shape)
                    }
                    write_netcdf(
                        os.path.join(file_path, '{0}_{1}{2}.nc'.format(pollutant_name, year, str(month).zfill(2))),
                        c_lats['data'], c_lons['data'], [emission], date=datetime(year=year, month=month, day=1),
                        boundary_latitudes=b_lats, boundary_longitudes=b_lons, cell_area=cell_area,
                        global_attributes=global_attributes)
        else:
            raise IOError('File not found {0}'.format(file_name))
    return True



if __name__ == '__main__':
    for y in LIST_YEARS:
        do_transformation(y)