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
from warnings import warn as warning
from datetime import datetime

# ============== README ======================
"""
downloading website: http://www.ceip.at/new_emep-grid/01_grid_data
reference: http://www.ceip.at/ms/ceip_home1/ceip_home/review_results/review_reports/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/ceip/emepv19/original_files'
OUTPUT_PATH = '/esarchive/recon/ceip/emepv19/yearly_mean'
INPUT_NAME = '<pollutant>_<sector>_2018_GRID_<year>.txt'
# list_years = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016,
# 2017]
LIST_YEARS = [2015]
LIST_POLLUTANTS = ['NOx', 'NMVOC', 'SOx', 'NH3', 'PM2_5', 'PM10', 'CO']
# ==============================================================


def correct_input_error(df):
    # TODO Documentation
    df.loc[df['LATITUDE'] == 36.14, 'LATITUDE'] = 36.15
    df.loc[df['LONGITUDE'] == 29.58, 'LONGITUDE'] = 29.55

    return df


def get_sectors():
    # TODO Documentation
    return ['A_PublicPower', 'B_Industry', 'C_OtherStationaryComb', 'D_Fugitive', 'E_Solvents', 'F_RoadTransport',
            'G_Shipping', 'H_Aviation', 'I_Offroad', 'J_Waste', 'K_AgriLivestock', 'L_AgriOther']


def calculate_grid_definition(in_path):
    # TODO Documentation
    import pandas as pd
    import numpy as np

    df = pd.read_table(in_path, sep=';', skiprows=[0, 1, 2, 3], names=[
        'ISO2', 'YEAR', 'SECTOR', 'POLLUTANT', 'LONGITUDE', 'LATITUDE', 'UNIT', 'EMISSION'])

    df = correct_input_error(df)
    # Longitudes
    lons = np.sort(np.unique(df.LONGITUDE))
    lons_interval = lons[1:] - lons[:-1]
    print('Lon min: {0}; Lon max: {1}; Lon inc: {2}; Lon num: {3}'.format(
        df.LONGITUDE.min(), df.LONGITUDE.max(), lons_interval.min(), len(lons)))

    # Latitudes
    lats = np.sort(np.unique(df.LATITUDE))
    lats_interval = lats[1:] - lats[:-1]
    print('Lat min: {0}; Lat max: {1}; Lat inc: {2}; Lat num: {3}'.format(
        df.LATITUDE.min(), df.LATITUDE.max(), lats_interval.min(), len(lats)))

    lats = np.arange(-90 + lats_interval.min()/2, 90, lats_interval.min(), dtype=np.float64)
    lons = np.arange(-180 + lons_interval.min()/2, 180, lons_interval.min(), dtype=np.float64)

    return lats, lons, lats_interval.min(), lons_interval.min()


def do_transformation(year):
    # TODO Documentation
    from hermesv3_gr.tools.netcdf_tools import write_netcdf, get_grid_area
    from hermesv3_gr.tools.coordinates_tools import create_bounds
    import pandas as pd
    import numpy as np

    unit_factor = 1000./(365.*24.*3600.)  # From Mg/year to Kg/s

    for pollutant in LIST_POLLUTANTS:
        for sector in get_sectors():
            in_file = os.path.join(
                INPUT_PATH,
                INPUT_NAME.replace('<year>', str(year)).replace('<sector>', sector).replace('<pollutant>', pollutant))

            if os.path.exists(in_file):
                print(in_file)
                c_lats, c_lons, lat_interval, lon_interval = calculate_grid_definition(in_file)
                b_lats = create_bounds(c_lats, number_vertices=2)
                b_lons = create_bounds(c_lons, number_vertices=2)
                name = pollutant.lower()
                if name == 'nox':
                    name = 'nox_no2'
                elif name == 'pm2_5':
                    name = 'pm25'
                elif name == 'sox':
                    name = 'so2'
                elif name == 'voc':
                    name = 'nmvoc'

                element = {
                    'name': name,
                    'units': 'kg.m-2.s-1',
                    'data': np.zeros((len(c_lats), len(c_lons)))
                }

                df = pd.read_table(
                    in_file, sep=';', skiprows=[0, 1, 2, 3],
                    names=['ISO2', 'YEAR', 'SECTOR', 'POLLUTANT', 'LONGITUDE', 'LATITUDE', 'UNIT', 'EMISSION'])

                df = correct_input_error(df)

                df['row_lat'] = np.array((df.LATITUDE - (-90 + lat_interval/2)) / lat_interval, dtype=np.int32)
                df['col_lon'] = np.array((df.LONGITUDE - (-180 + lon_interval/2)) / lon_interval, dtype=np.int32)

                df = df.groupby(['row_lat', 'col_lon']).sum().reset_index()

                element['data'][df.row_lat, df.col_lon] += df['EMISSION']

                element['data'] = element['data'].reshape((1,) + element['data'].shape)

                complete_output_dir = os.path.join(OUTPUT_PATH, '{0}_{1}'.format(element['name'], sector.lower()))
                if not os.path.exists(complete_output_dir):
                    os.makedirs(complete_output_dir)
                complete_output_dir = os.path.join(complete_output_dir, '{0}_{1}.nc'.format(element['name'], year))

                write_netcdf(complete_output_dir, c_lats, c_lons, [element], date=datetime(year, month=1, day=1),
                             boundary_latitudes=b_lats, boundary_longitudes=b_lons)
                cell_area = get_grid_area(complete_output_dir)
                element['data'] = element['data'] * unit_factor / cell_area
                write_netcdf(
                    complete_output_dir, c_lats, c_lons, [element], date=datetime(year, month=1, day=1),
                    boundary_latitudes=b_lats, boundary_longitudes=b_lons, cell_area=cell_area,
                    global_attributes={
                        'references': "web: http://www.ceip.at/ms/ceip_home1/ceip_home/webdab_emepdatabase/" +
                                      "emissions_emepmodels/",
                        'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                        '(Barcelona Supercomputing Center)'
                    })
            else:
                warning("The pollutant {0} for the GNFR14 sector {1} does not exist.\n File not found: {2}".format(
                    pollutant, sector, in_file))
    return True


if __name__ == '__main__':
    for y in LIST_YEARS:
        do_transformation(y)
