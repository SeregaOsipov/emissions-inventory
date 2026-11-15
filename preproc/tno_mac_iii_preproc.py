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

# ============== README ======================
"""
downloading website: contact to hugo.deniervandergon@tno.nl or jeroen.kuenen@tno.nl
reference: https://www.atmos-chem-phys.net/14/10963/2014/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/tno/tno_macc_iii/original_files/ascii'
OUTPUT_PATH = '/esarchive/recon/tno/tno_macc_iii/yearly_mean'
INPUT_NAME = 'TNO_MACC_III_emissions_v1_1_<year>.txt'
# list_years = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011]
LIST_YEARS = [2011]
VOC_RATIO_PATH = '/esarchive/recon/tno/tno_macc_iii/original_files/nmvoc'
VOC_RATIO_NAME = 'ratio_<voc>.nc'
# ==============================================================


def get_pollutants(in_path):
    """
    Find the pollutants on the ASCII emissions table.

    :param in_path: Path to the ASCII file that contains the information of the TNO_MAC-III emissions.
    :type in_path: str

    :return: List of the acronyms of the pollutants.
    :rtype: list
    """
    import pandas as pd

    columns = list(pd.read_table(in_path, sep=';', nrows=1).columns)
    return columns[6:]


def calculate_grid_definition(in_path):
    """
    Calculate the latitude and longitude coordinates of the cell.

    :param in_path: Path to the file that contains all the information.
    :type in_path: str

    :return: Latitudes array, Longitudes array, Latitude interval, Longitude interval.
    :rtype: numpy.array, numpy.array, float, float
    """
    import pandas as pd
    import numpy as np

    dataframe = pd.read_table(in_path, sep=';')
    dataframe = dataframe[dataframe.SourceType != 'P']

    # Longitudes
    lons = np.sort(np.unique(dataframe.Lon))
    lons_interval = lons[1:] - lons[:-1]
    print('Lon min: {0}; Lon max: {1}; Lon inc: {2}; Lon num: {3}'.format(
        dataframe.Lon.min(), dataframe.Lon.max(), lons_interval.min(), len(lons)))

    # Latitudes
    lats = np.sort(np.unique(dataframe.Lat))
    lats_interval = lats[1:] - lats[:-1]
    print('Lat min: {0}; Lat max: {1}; Lat inc: {2}; Lat num: {3}'.format(
        dataframe.Lat.min(), dataframe.Lat.max(), lats_interval.min(), len(lats)))

    lats = np.arange(-90 + lats_interval.min() / 2, 90, lats_interval.min(), dtype=np.float64)
    lons = np.arange(-180 + lons_interval.min() / 2, 180, lons_interval.min(), dtype=np.float64)

    return lats, lons, lats_interval.min(), lons_interval.min()


def create_pollutant_empty_list(in_path, len_c_lats, len_c_lons):
    """
    Crate an empty pollutant list.

    :param in_path: Path to the file that conains the information.
    :type in_path: str

    :param len_c_lats: Number of elements on the latitude array
    :type len_c_lats: int

    :param len_c_lons: Number of elements on the longitude array
    :type len_c_lons: int

    :return: Pollutant list
    :rtype: list
    """
    import numpy as np

    pollutant_list = []
    for pollutant in get_pollutants(in_path):
        aux_dict = {}
        if pollutant == 'PM2_5':
            aux_dict['name'] = 'pm25'
        elif pollutant == 'NOX':
            aux_dict['name'] = 'nox_no2'
        else:
            aux_dict['name'] = pollutant.lower()
        aux_dict['TNO_name'] = pollutant
        aux_dict['units'] = 'kg.m-2.s-1'
        # aux_dict['units'] = 'Mg.km-2.year-1'
        aux_dict['data'] = np.zeros((len_c_lats, len_c_lons))
        # aux_dict['data'] = np.zeros((len_c_lons, len_c_lats))
        pollutant_list.append(aux_dict)
    return pollutant_list


def do_transformation(year):
    """
    Make al the process to transform the emissions of the current year.

    :param year: year to process.
    :type year: int

    :return: True when everything finish well.
    :rtype: Bool
    """
    from hermesv3_gr.tools.netcdf_tools import write_netcdf, get_grid_area
    from hermesv3_gr.tools.coordinates_tools import create_bounds
    from datetime import datetime
    import pandas as pd
    import numpy as np

    in_file = os.path.join(INPUT_PATH, INPUT_NAME.replace('<year>', str(year)))

    unit_factor = 1000. / (365. * 24. * 3600.)  # To pass from Mg/year to Kg/s
    # unit_factor = 1000000  # To pass from Mg/m2.year to Mg/Km2.year

    c_lats, c_lons, lat_interval, lon_interval = calculate_grid_definition(in_file)

    b_lats = create_bounds(c_lats, number_vertices=2)
    b_lons = create_bounds(c_lons, number_vertices=2)

    dataframe = pd.read_table(in_file, sep=';')

    df_np = dataframe[dataframe.SourceType != 'P'].copy()
    df_p = dataframe[dataframe.SourceType == 'P'].copy()

    df_np.loc[:, 'row_lat'] = np.array((df_np.Lat - (-90 + lat_interval / 2)) / lat_interval, dtype=np.int32)
    df_np.loc[:, 'col_lon'] = np.array((df_np.Lon - (-180 + lon_interval / 2)) / lon_interval, dtype=np.int32)

    df_p.loc[:, 'row_lat'] = abs(np.array([c_lats] * len(df_p.Lat)) - df_p.Lat.values[:, None]).argmin(axis=1)
    df_p.loc[:, 'col_lon'] = abs(np.array([c_lons] * len(df_p.Lon)) - df_p.Lon.values[:, None]).argmin(axis=1)

    dataframe = pd.concat([df_np, df_p])

    for name, group in dataframe.groupby('SNAP'):
        print('snap', name)
        pollutant_list = create_pollutant_empty_list(in_file, len(c_lats), len(c_lons))

        # Other mobile sources ignoring sea cells (shipping emissions)
        if name == 8:
            for sea in ['ATL', 'BAS', 'BLS', 'MED', 'NOS']:
                group = group[group.ISO3 != sea]

        group = group.groupby(['row_lat', 'col_lon']).sum().reset_index()

        for i in range(len(pollutant_list)):
            # pollutant_list[i]['data'][group.col_lon, group.row_lat] = group[pollutant_list[i]['TNO_name']]
            pollutant_list[i]['data'][group.row_lat, group.col_lon] += group[pollutant_list[i]['TNO_name']]
            pollutant_list[i]['data'] = pollutant_list[i]['data'].reshape((1,) + pollutant_list[i]['data'].shape)
            # print pollutant_list[i]['data'].max()

            aux_output_path = os.path.join(OUTPUT_PATH, '{0}_snap{1}'.format(pollutant_list[i]['name'], name))
            if not os.path.exists(aux_output_path):
                os.makedirs(aux_output_path)
            aux_output_path = os.path.join(aux_output_path, '{0}_{1}.nc'.format(pollutant_list[i]['name'], year))
            write_netcdf(aux_output_path, c_lats, c_lons, [pollutant_list[i]], date=datetime(year, month=1, day=1),
                         boundary_latitudes=b_lats, boundary_longitudes=b_lons)
            cell_area = get_grid_area(aux_output_path)

            pollutant_list[i]['data'] = pollutant_list[i]['data'] * unit_factor/cell_area

            write_netcdf(aux_output_path, c_lats, c_lons, [pollutant_list[i]], date=datetime(year, month=1, day=1),
                         boundary_latitudes=b_lats, boundary_longitudes=b_lons, cell_area=cell_area,
                         global_attributes={
                             'references': 'J. J. P. Kuenen, A. J. H. Visschedijk, M. Jozwicka, and H. A. C. ' +
                                           'Denier van der Gon TNO-MACC_II emission inventory; a multi-year ' +
                                           '(2003-2009) consistent high-resolution European emission inventory ' +
                                           'for air quality modelling Atmospheric Chemistry and Physics 14 ' +
                                           '10963-10976 2014',
                             'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                                        '(Barcelona Supercomputing Center)'})
    return True


def extract_vars(netcdf_path, variables_list, attributes_list=()):
    """
    Get the data from the list of variabbles.

    :param netcdf_path: Path to the netCDF file
    :type netcdf_path: str

    :param variables_list: List of the names of the variables to get.
    :type variables_list: list

    :param attributes_list: List of the names of the variable attributes to get.
    :type attributes_list: list

    :return: List of the variables from the netCDF as a dictionary with data as values and with the other keys their
             attributes.
    :rtype: list.
    """
    from netCDF4 import Dataset
    data_list = []
    # print netcdf_path
    netcdf = Dataset(netcdf_path, mode='r')
    for var in variables_list:
        if var == 'emi_nox_no2':
            var1 = var
            var2 = 'emi_nox'
        else:
            var1 = var2 = var
        dict_aux = \
            {
                'name': var1,
                'data': netcdf.variables[var2][:],
            }
        for attribute in attributes_list:
            dict_aux.update({attribute: netcdf.variables[var2].getncattr(attribute)})
        data_list.append(dict_aux)
    netcdf.close()

    return data_list


def get_voc_ratio(ratio_path, snap):
    """
    Get the ratio of the VOC for the current SNAP.

    :param ratio_path: Path to the file with the ratios.
    :type ratio_path: str

    :param snap: SNAP to get the ratio.
    :type snap: str

    :return: VOC Ratio
    :rtype: dict
    """
    if snap == 'snap34':
        snap = 'snap3'
    try:
        [data_list] = extract_vars(ratio_path, [snap])
    except KeyError:
        return None
    return data_list


def get_voc_list():
    """
    Get the VOC list.

    :return: VOC list
    :rtype: list
    """
    return ['voc{0}'.format(str(x).zfill(2)) for x in [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                                       21, 22, 23, 24, 25]]


def get_sector_list():
    """
    Get the sector list.

    :return: Sector list
    :rtype: list
    """
    return ['snap{0}'.format(x) for x in [1, 2, 34, 5, 6, 71, 72, 73, 74, 8, 9]]


def do_voc_transformation(year):
    """
    Make al the process to transform the VOC emissions of the current year.

    :param year: year to process.
    :type year: int

    :return: True when everything finish well.
    :rtype: Bool
    """
    from warnings import warn as warning
    from hermesv3_gr.tools.netcdf_tools import write_netcdf, extract_vars
    from hermesv3_gr.tools.coordinates_tools import create_bounds

    for snap in get_sector_list():
        in_path = os.path.join(OUTPUT_PATH, 'nmvoc_{0}'.format(snap), 'nmvoc_{0}.nc'.format(year))
        [nmvoc, c_lats, c_lons, cell_area] = extract_vars(in_path, ['nmvoc', 'lat', 'lon', 'cell_area'])
        for voc in get_voc_list():
            ratio_path = os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', voc))
            ratios_dict = get_voc_ratio(ratio_path, snap)
            if ratios_dict is not None:
                new_voc = {
                    'name': voc,
                    'units': 'kg.m-2.s-2'
                }

                b_lats = create_bounds(c_lats['data'], number_vertices=2)
                b_lons = create_bounds(c_lons['data'], number_vertices=2)
                mask = ratios_dict['data']

                new_voc['data'] = nmvoc['data'] * mask

                out_dir_aux = os.path.join(OUTPUT_PATH, '{0}_{1}'.format(voc, snap))
                if not os.path.exists(out_dir_aux):
                    os.makedirs(out_dir_aux)
                # print os.path.join(out_dir_aux, '{0}_{1}.nc'.format(voc, year))
                write_netcdf(os.path.join(out_dir_aux, '{0}_{1}.nc'.format(voc, year)), c_lats['data'],
                             c_lons['data'], [new_voc], boundary_latitudes=b_lats, boundary_longitudes=b_lons,
                             cell_area=cell_area['data'],
                             global_attributes={
                                 'references': 'J. J. P. Kuenen, A. J. H. Visschedijk, M. Jozwicka, and H. A. C. ' +
                                               'Denier van der Gon TNO-MACC_II emission inventory; a multi-year ' +
                                               '(2003-2009) consistent high-resolution European emission inventory ' +
                                               'for air quality modelling Atmospheric Chemistry and Physics 14 ' +
                                               '10963-10976 2014',
                                 'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                                            '(Barcelona Supercomputing Center)'})
            else:
                warning("The pollutant {0} for the sector {1} does not exist.\n SNAP not found: {2}".format(
                    voc, snap, ratio_path))

    return True


def check_vocs(year):
    """
    Check that the VOCs are calculated correctly.

    :param year: Year to evaluate
    :type year: int

    :return: True when finish.
    :rtype: bool
    """
    for snap in get_sector_list():
        nmvoc_path = os.path.join(OUTPUT_PATH, 'nmvoc_{0}'.format(snap), 'nmvoc_{0}.nc'.format(year))
        [new_voc] = extract_vars(nmvoc_path, ['nmvoc'])
        nmvoc_sum = new_voc['data'].sum()

        voc_sum = 0
        for voc in get_voc_list():
            voc_path = os.path.join(OUTPUT_PATH, '{0}_{1}'.format(voc, snap), '{0}_{1}.nc'.format(voc, year))
            if os.path.exists(voc_path):
                [new_voc] = extract_vars(voc_path, [voc])
                voc_sum += new_voc['data'].sum()

        print('{0} NMVOC sum: {1}; VOCs sum: {2}; %diff: {3}'.format(
            snap, nmvoc_sum, voc_sum, 100*(nmvoc_sum - voc_sum) / nmvoc_sum))
    return True


if __name__ == '__main__':
    for y in LIST_YEARS:
        do_transformation(y)
        do_voc_transformation(y)
        # check_vocs(y)
