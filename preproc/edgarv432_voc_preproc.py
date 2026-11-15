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

# ============== README ======================
"""
downloading website: http://edgar.jrc.ec.europa.eu/overview.php?v=432_VOC_spec
reference: https://www.atmos-chem-phys.net/17/7683/2017/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/jrc/edgarv432_voc/original_files/'
OUTPUT_PATH = '/esarchive/recon/jrc/edgarv432_voc'
LIST_POLLUTANTS = ['voc1', 'voc2', 'voc3', 'voc4', 'voc5', 'voc6', 'voc7', 'voc8', 'voc9', 'voc10', 'voc11', 'voc12',
                   'voc13', 'voc14', 'voc15', 'voc16', 'voc17', 'voc18', 'voc19', 'voc20', 'voc21', 'voc22', 'voc23',
                   'voc24', 'voc25']
# list_years = [1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986,
#               1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003,
#               2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012]
LIST_YEARS = [2010]

# To do yearly emissions
PROCESS_YEARLY = True
YEARLY_INPUT_NAME = 'yearly/v432_VOC_spec_<pollutant>_<year>_<ipcc>.0.1x0.1.nc'

# To process monthly emissions, 2010 directly from monthly_input_name and other years calculated using monthly gridded factors derived from the 2010 monthly data
PROCESS_MONTHLY = False
MONTHLY_INPUT_NAME = 'monthly/v432_VOC_spec_<pollutant>_2010_<month>_<ipcc>.0.1x0.1.nc'
MONTHLY_PATTERN_FILE = 'temporal_profiles/v432_FM_<sector>.0.1x0.1.nc'
# ==============================================================

"""
Main script to transform EDGARv4.3.2 AP global emission inventory to a NetCDF that follows the CF-1.6 conventions.

This script also calculates the boundaries of teh cells and teh cell area.

Carles Tena Medina (carles.tena@bsc.es) from Barcelona Supercomputing Center (BSC-CNS).
"""


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




def ipcc_to_sector_dict():
    # TODO Documentation
    ipcc_sector_dict = {
        "IPCC_4F": "AWB",
        "IPCC_1A1": "ENE",
        "IPCC_7A": "FFF",
        "IPCC_1A2": "IND",
        "IPCC_2_3": "PPA",
        "IPCC_1B1a_1B2a1_1B2a2_1B2a3_1B2a4_1B2c": "PRO",
        "IPCC_1A4": "RCO",
        "IPCC_1A1b_1B2a5": "REF",
        "IPCC_6": "SWD",
        "IPCC_1A3a_CDS": "TNR_Aviation_CDS",
        "IPCC_1A3a_CRS": "TNR_Aviation_CRS",
        "IPCC_1A3a_LTO": "TNR_Aviation_LTO",
        "IPCC_1A3c_1A3e": "TNR_Other",
        "IPCC_1A3d_1C2": "TNR_Ship",
        "IPCC_1A1c_1A5b1_1B1b_1B2a6_1B2b5_2C1b": "TRF",
        "IPCC_1A3b": "TRO"
    }

    return ipcc_sector_dict


def write_netcdf(output_name_path, data, data_atts, center_lats, center_lons, grid_cell_area, year, sector,
                 month=None):
    # TODO Documentation
    # Creating NetCDF & Dimensions
    print(output_name_path)
    nc_output = Dataset(output_name_path, mode='w', format="NETCDF4")
    nc_output.createDimension('nv', 2)
    nc_output.createDimension('lon', center_lons.shape[0])
    nc_output.createDimension('lat', center_lats.shape[0])
    nc_output.createDimension('time', None)

    # TIME
    time = nc_output.createVariable('time', 'd', ('time',), zlib=True)
    # time.units = "{0} since {1}".format(tstep_units, global_atts['Start_DateTime'].strftime('%Y-%m-%d %H:%M:%S'))
    if month is None:
        time.units = "years since {0}-01-01 00:00:00".format(year)
    else:
        time.units = "months since {0}-{1}-01 00:00:00".format(year, str(month).zfill(2))
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
    nc_var = nc_output.createVariable(data_atts['long_name'], 'f', ('time', 'lat', 'lon',), zlib=True)
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

    nc_output.setncattr('title', 'EDGARv4.3.2_AP inventory for the sector {0} and pollutant {1}'.format(
        sector, data_atts['long_name']), )
    nc_output.setncattr('Conventions', 'CF-1.6', )
    nc_output.setncattr('institution', 'JRC', )
    nc_output.setncattr('source', 'EDGARv4.3.2_AP', )
    nc_output.setncattr('history', 'Re-writing of the EDGAR input to follow the CF 1.6 conventions;\n' +
                        '2017-03-22: Added time dimension (UNLIMITED);\n' +
                        '2017-03-22: Added boundaries;\n' +
                        '2017-03-24: Added global attributes;\n' +
                        '2017-03-24: Re-naming pollutant;\n' +
                        '2017-04-03: Added cell_area variable;\n')

    nc_output.setncattr('references', 'web: http://edgar.jrc.ec.europa.eu/overview.php?v=432_VOC_spec\n' +
                        'publication: Huang et al. (ACP, 2017)', )
    nc_output.setncattr('comment', 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                        '(Barcelona Supercomputing Center)', )

    nc_output.close()

    return True


def do_yearly_transformation(year):
    # TODO Documentation
    print(year)
    for pollutant in LIST_POLLUTANTS:
        for ipcc in list(ipcc_to_sector_dict().keys()):
            file_path = os.path.join(
                INPUT_PATH,
                YEARLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<ipcc>',
                                                                                                         ipcc))

            if os.path.exists(file_path):
                grid_area = get_grid_area(file_path)
                print(file_path)
                nc_in = Dataset(file_path, mode='r')

                data = nc_in.variables['emi_{0}'.format(pollutant.lower())][:]

                data = np.array(data)

                # Reading lat, lon
                lats = nc_in.variables['lat'][:]
                lons = nc_in.variables['lon'][:]
                nc_in.close()

                sector = ipcc_to_sector_dict()[ipcc]
                if pollutant in ['voc{0}'.format(x) for x in range(1, 9 + 1, 1)]:
                    pollutant_aux = pollutant.replace('voc', 'voc0')
                else:
                    pollutant_aux = pollutant

                data_attributes = {'long_name': pollutant_aux.lower(),
                                   'units': 'kg.m-2.s-1',
                                   'coordinates': 'lat lon',
                                   'grid_mapping': 'crs'}
                out_path_aux = os.path.join(OUTPUT_PATH, 'yearly_mean', pollutant_aux.lower() + '_' + sector.lower())
                if not os.path.exists(out_path_aux):
                    os.makedirs(out_path_aux)
                # print os.path.join(out_path_aux, '{0}_{1}.nc'.format(pollutant_aux.lower(), year))
                write_netcdf(os.path.join(out_path_aux, '{0}_{1}.nc'.format(pollutant_aux.lower(), year)),
                             data, data_attributes, lats, lons, grid_area, year, sector.lower())

            else:
                warning("The pollutant {0} for the IPCC sector {1} does not exist.\n File not found: {2}".format(
                    pollutant, ipcc, file_path))
    return True


def do_monthly_transformation(year):
    # TODO Documentation
    print(year)
    for pollutant in LIST_POLLUTANTS:
        for ipcc in list(ipcc_to_sector_dict().keys()):
            file_path = os.path.join(
                INPUT_PATH,
                YEARLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<ipcc>',
                                                                                                         ipcc))

            if os.path.exists(file_path):
                grid_area = get_grid_area(file_path)
                print(file_path)
                nc_in = Dataset(file_path, mode='r')

                data = nc_in.variables['emi_{0}'.format(pollutant.lower())][:]

                data = np.array(data)

                # Reading lat, lon
                lats = nc_in.variables['lat'][:]
                lons = nc_in.variables['lon'][:]
                nc_in.close()

                sector = ipcc_to_sector_dict()[ipcc]

                if pollutant in ['voc{0}'.format(x) for x in range(1, 9 + 1, 1)]:
                    pollutant_aux = pollutant.replace('voc', 'voc0')
                else:
                    pollutant_aux = pollutant

                data_attributes = {'long_name': pollutant_aux.lower(),
                                   'units': 'kg.m-2.s-1',
                                   'coordinates': 'lat lon',
                                   'grid_mapping': 'crs'}

                out_path_aux = os.path.join(OUTPUT_PATH, 'monthly_mean', pollutant_aux.lower() + '_' + sector.lower())
                if not os.path.exists(out_path_aux):
                    os.makedirs(out_path_aux)

                nc_month_factors = Dataset(os.path.join(INPUT_PATH, MONTHLY_PATTERN_FILE.replace('<sector>', sector)))
                month_factors = nc_month_factors.variables[sector][:]
                for month in range(1, 12 + 1, 1):
                    data_aux = data * month_factors[month - 1, :, :]
                    write_netcdf(os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(
                        pollutant_aux.lower(), year, str(month).zfill(2))),
                                 data_aux, data_attributes, lats, lons, grid_area, year, sector.lower())

            else:
                warning(
                    "The pollutant {0} for the IPCC sector {1} does not exist.\n File not found: {2}".format(
                        pollutant, ipcc, file_path))
    return True


def do_2010_monthly_transformation():
    # TODO Documentation
    for pollutant in LIST_POLLUTANTS:
        for ipcc in list(ipcc_to_sector_dict().keys()):
            for month in range(1, 12 + 1, 1):
                file_path = os.path.join(
                    INPUT_PATH,
                    MONTHLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<month>',
                                                                                 str(month)).replace('<ipcc>', ipcc))

                if os.path.exists(file_path):
                    grid_area = get_grid_area(file_path)
                    print(file_path)
                    nc_in = Dataset(file_path, mode='r')

                    data = nc_in.variables['emi_{0}'.format(pollutant.lower())][:]

                    data = np.array(data)

                    # Reading lat, lon
                    lats = nc_in.variables['lat'][:]
                    lons = nc_in.variables['lon'][:]
                    nc_in.close()

                    sector = ipcc_to_sector_dict()[ipcc]

                    if pollutant in ['voc{0}'.format(x) for x in range(1, 9 + 1, 1)]:
                        pollutant_aux = pollutant.replace('voc', 'voc0')
                    else:
                        pollutant_aux = pollutant

                    data_attributes = {'long_name': pollutant_aux.lower(),
                                       'units': 'kg.m-2.s-1',
                                       'coordinates': 'lat lon',
                                       'grid_mapping': 'crs'}

                    out_path_aux = os.path.join(
                        OUTPUT_PATH, 'monthly_mean', pollutant_aux.lower() + '_' + sector.lower())
                    if not os.path.exists(out_path_aux):
                        os.makedirs(out_path_aux)
                    write_netcdf(os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(
                        pollutant_aux.lower(), 2010, str(month).zfill(2))),
                                 data, data_attributes, lats, lons, grid_area, 2010, sector.lower())

                else:
                    warning("The pollutant {0} for the IPCC sector {1} does not exist.\n File not found: {2}".format(
                        pollutant, ipcc, file_path))
    return True


if __name__ == '__main__':

    if PROCESS_YEARLY:
        for y in LIST_YEARS:
            do_yearly_transformation(y)

    if PROCESS_MONTHLY:
        for y in LIST_YEARS:
            if y == 2010:
                do_2010_monthly_transformation()
            else:
                do_monthly_transformation(y)
