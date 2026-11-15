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
downloading website: ¿¿¿???
reference: ¿¿¿???
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/uchile/cr2_dgf/original_files/emis_<sector>_v20190928/<year>/<in_poll>-<year>.nc'
OUTPUT_PATH = '/esarchive/recon/uchile/cr2_dgf/'
LIST_POLLUTANTS = ['bc', 'ch4', 'co', 'co2', 'nox_no2', 'pm25', 'nmvoc']
SECTOR_LIST = {'TRA': 'road_transport'}

YEAR_LIST = [2013, 2014, 2015, 2016, 2017]
# YEAR_LIST = [2015]
# ==============================================================


def get_pollutant_dict(sector):
    if sector == 'TRA':
        pollutant_dict = {
            'bc': {'file': 'BC', 'var': 'BC'},
            'ch4': {'file': 'CH4', 'var': 'CH4'},
            'co': {'file': 'CO-', 'var': 'CO'},
            'co2': {'file': 'CO2', 'var': 'CO2'},
            'nox_no2': {'file': 'NOx', 'var': 'NOx'},
            'pm25': {'file': 'PM25', 'var': 'PM25'},
            'nmvoc': {'file': 'VOC', 'var': 'VOC'},
        }

    return pollutant_dict


def do_transformation():
    from hermesv3_gr.tools.netcdf_tools import write_netcdf, get_grid_area
    from hermesv3_gr.tools.coordinates_tools import create_bounds
    import calendar
    import numpy as np
    from datetime import datetime

    lats = lons = blats = blons = cell_area = None

    for sector in SECTOR_LIST.keys():
        pollutant_dict = get_pollutant_dict(sector)
        for year in YEAR_LIST:
            for pollutant in pollutant_dict.keys():
                out_file_name = os.path.join(OUTPUT_PATH, 'yearly_mean',
                                             '{0}_{1}'.format(pollutant, SECTOR_LIST[sector]),
                                             "{0}_{1}.nc".format(pollutant, year))
                file_name = INPUT_PATH.replace('<year>', str(year)).replace('<sector>', sector).replace(
                    '<in_poll>', pollutant_dict[pollutant]['file'])

                netcdf = Dataset(file_name, mode='r')
                if lats is None:
                    lat_nc = netcdf.variables['lat'][:]
                    lon_nc = netcdf.variables['lon'][:]
                    lat_inc = round(lat_nc[1] - lat_nc[0], 5)
                    lon_inc = round(lon_nc[1] - lon_nc[0], 5)

                    lats = np.linspace(lat_nc[0], lat_nc[0] + (lat_inc * (len(lat_nc) - 1)), len(lat_nc),
                                       dtype=np.float)
                    lons = np.linspace(lon_nc[0], lon_nc[0] + (lon_inc * (len(lon_nc) - 1)), len(lon_nc),
                                       dtype=np.float)
                    del lat_nc, lon_nc
                    blats = create_bounds(lats)
                    blons = create_bounds(lons)
                    cell_area = get_grid_area(file_name)

                var = netcdf.variables[pollutant_dict[pollutant]['var']][:]

                if calendar.isleap(year):
                    days = 366
                else:
                    days = 365

                # from ton/yr to kg/m2.s
                var = (var / cell_area) * (1000 / (days * 24 * 60 * 60))

                data = [{'name': pollutant, 'units': 'kg.m-2.s-1', 'data': var.reshape((1,) + var.shape)}]

                if not os.path.exists(os.path.dirname(out_file_name)):
                    os.makedirs(os.path.dirname(out_file_name))
                print(out_file_name)
                write_netcdf(out_file_name, lats, lons, data, date=datetime(year=year, month=1, day=1),
                             boundary_latitudes=blats, boundary_longitudes=blons, cell_area=cell_area,
                             regular_latlon=True)


if __name__ == '__main__':
    starting_time = timeit.default_timer()

    do_transformation()

    print('Time(s):', timeit.default_timer() - starting_time)
