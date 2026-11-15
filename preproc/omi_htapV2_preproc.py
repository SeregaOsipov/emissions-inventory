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

__author__ = 'Sergey Osipov <Serega.Osipov@gmail.com>'

# ============== README ======================
"""

htapv2_preproc.py was used as a template

downloading website: https://avdc.gsfc.nasa.gov/pub/data/project/OMI_HTAP_emis/
reference: 
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = os.environ.get('OMI_HTAP_INPUT_PATH', '/HDD1/Data/emissions/OMI-HTAP')
OUTPUT_PATH = os.environ.get('OMI_HTAP_OUTPUT_PATH', os.path.join(INPUT_PATH, 'hermesv3_gr_pp'))

INPUT_NAME = 'htapv2.2.emisso2.<sector>.x3600y1800t12.<year>.integrate.nc4'

# list_years = [2008, 2010]
LIST_YEARS = [2017]


def do_transformation(filename_list, out_path, pollutant, sector, year):
    """
    Re-write the OMI-HTAPv2 inputs following ES anc CF-1.6 conventions.

    :param filename_list: List of input file names.
    :type filename_list: list

    :param out_path: Path to store the output.
    :type out_path: str

    :param pollutant: Pollutant name.
    :type pollutant: str

    :param sector: Name of the sector.
    :type sector: str

    :param year: Year.
    :type year: int

    :return:
    """
    from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf, get_grid_area
    from hermesv3_gr.tools.coordinates_tools import create_bounds

    # file name that holds netcdf for one year with 12 months
    filename = filename_list[0]
    print('Processing input: {}'.format(filename))
    [c_lats, c_lons] = extract_vars(filename, ['lat', 'lon'])

    var_key = 'sanl1'  # surface
    if sector == 'elevated':
        var_key = 'sanl2'

    print('Var key is: {}'.format(var_key))

    [data_12_months] = extract_vars(filename, [var_key], attributes_list=['standard_name', 'units', 'cell_method', 'long_name'])

    for month in range(0, 12):
        data = data_12_months.copy()
        data['data'] = data_12_months['data'][month].reshape((1,) + data_12_months['data'][month].shape)
        data['name'] = pollutant

        global_attributes = {
            'title': 'OMI-HTAPv2 inventory for the sector {0} and pollutant {1}'.format(sector, data['long_name']),
            'Conventions': 'CF-1.6',
            'source': 'OMI-HTAPv2',
            'history': '15-06-2020: first implementation;\n',
            'comment': 'Re-writing done by Sergey Osipov (Serega.Osipov@gmail.com) from MPIC ' +
                       '(Max Planck Institute for Chemistry)',
        }

        out_path_aux = os.path.join(out_path, pollutant + '_' + sector.lower())
        if not os.path.exists(out_path_aux):
            os.makedirs(out_path_aux)

        out_path_aux = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(pollutant, year, str(month+1).zfill(2)))
        write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [data],
                     boundary_latitudes=create_bounds(c_lats['data']), boundary_longitudes=create_bounds(c_lons['data']),
                     cell_area=get_grid_area(filename), global_attributes=global_attributes,)

        print('Saved output to: {}'.format(out_path_aux))

    return True


def get_pollutant_dict():
    # TODO Documentation
    """

    :return:
    """
    p_dict = {
        'so2': 'SO2',
    }
    return p_dict


def get_sector_dict():
    # TODO Documentation
    """

    :return:
    """
    common_dict = {
        'month': ['surface', 'elevated'],
    }
    sector_dict = {
        'so2': common_dict,
    }
    return sector_dict


if __name__ == '__main__':
    for year in LIST_YEARS:
        for pollutant_dict in get_pollutant_dict().items():
            for current_sector in get_sector_dict()[pollutant_dict[0]]['month']:
                print('Processing sector: {}'.format(current_sector))
                input_name_aux = INPUT_NAME.replace('<sector>', current_sector)
                input_name_aux = input_name_aux.replace('<year>', str(year))
                files = [os.path.join(INPUT_PATH, input_name_aux),]
                do_transformation(files, os.path.join(OUTPUT_PATH, 'monthly_mean'), pollutant_dict[0], current_sector, year)
