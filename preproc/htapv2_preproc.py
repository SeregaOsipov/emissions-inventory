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
downloading website: http://edgar.jrc.ec.europa.eu/htap_v2/
reference: https://www.atmos-chem-phys.net/15/11411/2015/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/jrc/htapv2/original_files'
OUTPUT_PATH = '/esarchive/recon/jrc/htapv2'

INPUT_NAME = 'edgar_HTAP_<pollutant>_emi_<sector>_<year>_<month>.0.1x0.1.nc'
INPUT_NAME_AIR = 'edgar_HTAP_emi_<pollutant>_<sector>_<year>.0.1x0.1.nc'
INPUT_NAME_SHIPS = 'edgar_HTAP_<pollutant>_emi_SHIPS_<year>.0.1x0.1.nc'
# HTAP auxiliary NMVOC emission data for the industry sub-sectors
#     (http://iek8wikis.iek.fz-juelich.de/HTAPWiki/WP1.1?highlight=%28%28WP1.1%29%29)
INPUT_NAME_NMVOC_INDUSTRY = 'HTAPv2_NMVOC_<sector>_<year>_<month>.0.1x0.1.nc'

# list_years = [2008, 2010]
LIST_YEARS = [2010]

# RETRO ratios applied to HTAPv2 NMVOC emissions
#      (http://iek8wikis.iek.fz-juelich.de/HTAPWiki/WP1.1?highlight=%28%28WP1.1%29%29)
VOC_RATIO_PATH = '/esarchive/recon/jrc/htapv2/original_files/retro_nmvoc_ratio_2000_01x01'
VOC_RATIO_NAME = 'retro_nmvoc_ratio_<voc>_2000_0.1deg.nc'
VOC_RATIO_AIR_NAME = 'VOC_split_AIR.csv'
VOC_RATIO_SHIPS_NAME = 'VOC_split_SHIP.csv'
# ==============================================================


def do_transformation_annual(filename, out_path, pollutant, sector, year):
    """
    Re-write the HTAPv2 inputs following ES anc CF-1.6 conventions for annual inventories.

    :param filename: Path to the input file.
    :type filename: str

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
    print(filename)
    [c_lats, c_lons] = extract_vars(filename, ['lat', 'lon'])

    if pollutant == 'pm25':
        [data] = extract_vars(filename, ['emi_pm2.5'],
                              attributes_list=['standard_name', 'units', 'cell_method', 'long_name'])
    else:
        [data] = extract_vars(filename, ['emi_{0}'.format(pollutant)],
                              attributes_list=['standard_name', 'units', 'cell_method', 'long_name'])
    data['data'] = data['data'].reshape((1,) + data['data'].shape)
    data['name'] = pollutant

    global_attributes = {
        'title': 'HTAPv2 inventory for the sector {0} and pollutant {1}'.format(sector, data['long_name']),
        'Conventions': 'CF-1.6',
        'institution': 'European Commission, Joint Research Centre (JRC)',
        'source': 'HTAPv2',
        'history': 'Re-writing of the HTAPv2 input to follow the CF 1.6 conventions;\n' +
                   '2017-04-04: Added time dimension (UNLIMITED);\n' +
                   '2017-04-04: Added boundaries;\n' +
                   '2017-04-04: Added global attributes;\n' +
                   '2017-04-04: Re-naming pollutant;\n' +
                   '2017-04-04: Added cell_area variable;\n',
        'references': 'EC, JRC / US EPA, HTAP_V2. ' +
                      'http://edgar.jrc.ec.europa.eu/htap/EDGAR-HTAP_v1_final_jan2012.pdf\n ' +
                      'http://edgar.jrc.ec.europa.eu/htap_v2/',
        'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                   '(Barcelona Supercomputing Center)',
    }

    out_path = os.path.join(out_path, pollutant + '_' + sector.lower())
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    out_path = os.path.join(out_path, '{0}_{1}.nc'.format(pollutant, year))
    print(out_path)
    write_netcdf(out_path, c_lats['data'], c_lons['data'], [data],
                 boundary_latitudes=create_bounds(c_lats['data']), boundary_longitudes=create_bounds(c_lons['data']),
                 cell_area=get_grid_area(filename), global_attributes=global_attributes,)
    return True


def do_transformation(filename_list, out_path, pollutant, sector, year):
    """
    Re-write the HTAPv2 inputs following ES anc CF-1.6 conventions.

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

    for month in range(1, 13):
        print(filename_list[month - 1])
        [c_lats, c_lons] = extract_vars(filename_list[month - 1], ['lat', 'lon'])

        if pollutant == 'pm25':
            [data] = extract_vars(filename_list[month - 1], ['emi_pm2.5'],
                                  attributes_list=['standard_name', 'units', 'cell_method', 'long_name'])
        else:
            [data] = extract_vars(filename_list[month - 1], ['emi_{0}'.format(pollutant)],
                                  attributes_list=['standard_name', 'units', 'cell_method', 'long_name'])
        data['data'] = data['data'].reshape((1,) + data['data'].shape)
        data['name'] = pollutant

        global_attributes = {
            'title': 'HTAPv2 inventory for the sector {0} and pollutant {1}'.format(sector, data['long_name']),
            'Conventions': 'CF-1.6',
            'institution': 'European Commission, Joint Research Centre (JRC)',
            'source': 'HTAPv2',
            'history': 'Re-writing of the HTAPv2 input to follow the CF 1.6 conventions;\n' +
                       '2017-04-04: Added time dimension (UNLIMITED);\n' +
                       '2017-04-04: Added boundaries;\n' +
                       '2017-04-04: Added global attributes;\n' +
                       '2017-04-04: Re-naming pollutant;\n' +
                       '2017-04-04: Added cell_area variable;\n',
            'references': 'publication: Janssens-Maenhout, G., et al.: HTAP_v2.2: a mosaic of regional and  global ' +
                          'emission grid maps for 2008 and 2010 to study hemispheric  transport of air pollution, ' +
                          'Atmos. Chem. Phys., 15, 11411-11432,  https://doi.org/10.5194/acp-15-11411-2015, 2015.\n ' +
                          'web: http://edgar.jrc.ec.europa.eu/htap_v2/index.php',
            'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                       '(Barcelona Supercomputing Center)',
        }

        out_path_aux = os.path.join(out_path, pollutant + '_' + sector.lower())
        if not os.path.exists(out_path_aux):
            os.makedirs(out_path_aux)

        out_path_aux = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(pollutant, year, str(month).zfill(2)))
        write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [data],
                     boundary_latitudes=create_bounds(c_lats['data']), boundary_longitudes=create_bounds(c_lons['data']),
                     cell_area=get_grid_area(filename_list[month - 1]), global_attributes=global_attributes,)
    return True


def do_ratio_list(sector=None):
    # TODO Documentation
    """

    :param sector:
    :return:
    """
    if sector == 'SHIPS':
        return {'all': os.path.join(VOC_RATIO_PATH, VOC_RATIO_SHIPS_NAME)}
    elif sector == 'AIR_CDS':
        return {'all': os.path.join(VOC_RATIO_PATH, VOC_RATIO_AIR_NAME)}
    elif sector == 'AIR_CRS':
        return {'all': os.path.join(VOC_RATIO_PATH, VOC_RATIO_AIR_NAME)}
    elif sector == 'AIR_LTO':
        return {'all': os.path.join(VOC_RATIO_PATH, VOC_RATIO_AIR_NAME)}
    return {
        'voc01': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '01')),
        'voc02': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '02')),
        'voc03': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '03')),
        'voc04': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '04')),
        'voc05': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '05')),
        'voc06': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '06')),
        'voc07': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '07')),
        'voc08': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '08')),
        'voc09': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '09')),
        'voc12': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '12')),
        'voc13': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '13')),
        'voc14': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '14')),
        'voc15': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '15')),
        'voc16': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '16')),
        'voc17': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '17')),
        'voc18': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '18')),
        'voc19': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '19')),
        'voc20': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '20')),
        'voc21': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '21')),
        'voc22': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '22')),
        'voc23': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '23')),
        'voc24': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '24')),
        'voc25': os.path.join(VOC_RATIO_PATH, VOC_RATIO_NAME.replace('<voc>', '25')),
    }


def do_nmvoc_month_transformation(filename_list, out_path, sector, year):
    # TODO Docuemtnation
    """

    :param filename_list:
    :param out_path:
    :param sector:
    :param year:
    :return:
    """
    from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf
    from hermesv3_gr.tools.coordinates_tools import create_bounds

    nmvoc_ratio_list = do_ratio_list()

    print(sector)
    if sector == 'ENERGY':
        ratio_var = 'pow'

        nmvoc_ratio_list.pop('voc18', None)
        nmvoc_ratio_list.pop('voc19', None)
        nmvoc_ratio_list.pop('voc20', None)

    elif sector == 'RESIDENTIAL':
        ratio_var = 'res'

        nmvoc_ratio_list.pop('voc18', None)
        nmvoc_ratio_list.pop('voc20', None)

    elif sector == 'TRANSPORT':
        ratio_var = 'tra'

        nmvoc_ratio_list.pop('voc01', None)
        nmvoc_ratio_list.pop('voc18', None)
        nmvoc_ratio_list.pop('voc19', None)
        nmvoc_ratio_list.pop('voc20', None)
        nmvoc_ratio_list.pop('voc24', None)
        nmvoc_ratio_list.pop('voc25', None)

    print(type(nmvoc_ratio_list), nmvoc_ratio_list)

    for month in range(1, 13):
        print(filename_list[month - 1])
        c_lats, c_lons = extract_vars(filename_list[month - 1], ['lat', 'lon'])

        [data] = extract_vars(filename_list[month - 1], ['emi_nmvoc'])

        for voc, ratio_file in nmvoc_ratio_list.items():
            print(voc, ratio_file)

            pollutant = voc
            [ratio] = extract_vars(ratio_file, [ratio_var])

            data_aux = data.copy()
            data_aux['data'] = data['data'] * ratio['data']
            data_aux['data'] = data_aux['data'].reshape((1,) + data_aux['data'].shape)
            data_aux['name'] = voc
            data_aux['units'] = 'kg m-2 s-1'
            global_attributes = {
                'title': 'HTAPv2 inventory for the sector {0} and pollutant {1}'.format(sector, pollutant),
                'Conventions': 'CF-1.6',
                'institution': 'European Commission, Joint Research Centre (JRC)',
                'source': 'HTAPv2',
                'history': 'Re-writing of the HTAPv2 input to follow the CF 1.6 conventions;\n' +
                           '2017-04-28: ...',
                'references': 'publication: Janssens-Maenhout, G., et al.: HTAP_v2.2: a mosaic of regional and ' +
                              'global emission grid maps for 2008 and 2010 to study hemispheric  transport of air ' +
                              'pollution, Atmos. Chem. Phys., 15, 11411-11432, ' +
                              'https://doi.org/10.5194/acp-15-11411-2015, 2015.\n ' +
                              'web: http://edgar.jrc.ec.europa.eu/htap_v2/index.php',
                'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                           '(Barcelona Supercomputing Center)',
            }

            out_path_aux = os.path.join(out_path, pollutant + '_' + sector.lower())
            if not os.path.exists(out_path_aux):
                os.makedirs(out_path_aux)

            out_path_aux = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(pollutant, year, str(month).zfill(2)))
            print(out_path_aux)
            write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [data_aux],
                         boundary_latitudes=create_bounds(c_lats['data']),
                         boundary_longitudes=create_bounds(c_lons['data']), global_attributes=global_attributes,)
    return True


def do_nmvoc_industry_month_transformation(filename_list, out_path, sector, year):
    # TODO Documentation
    """

    :param filename_list:
    :param out_path:
    :param sector:
    :param year:
    :return:
    """
    from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf
    from hermesv3_gr.tools.coordinates_tools import create_bounds

    nmvoc_ratio_list = do_ratio_list()

    print(sector)

    print(type(nmvoc_ratio_list), nmvoc_ratio_list)

    for month in range(1, 13):
        print(filename_list[month - 1])
        c_lats, c_lons = extract_vars(filename_list[month - 1], ['lat', 'lon'])

        [ind, exf, sol] = extract_vars(filename_list[month - 1], ['emiss_ind', 'emiss_exf', 'emiss_sol'])

        for voc, ratio_file in nmvoc_ratio_list.items():
            print(voc, ratio_file)
            data = {
                'name': voc,
                'units': 'kg m-2 s-1',
            }
            if voc in ['voc02', 'voc03', 'voc04', 'voc05', 'voc07', 'voc08', 'voc12', 'voc13']:
                [r_inc, r_exf] = extract_vars(ratio_file, ['inc', 'exf'])
                data.update({'data': ind['data'] * r_inc['data'] + exf['data'] * r_exf['data']})
            elif voc in ['voc01', 'voc23', 'voc25']:
                [r_inc, r_sol] = extract_vars(ratio_file, ['inc', 'sol'])
                data.update({'data': ind['data'] * r_inc['data'] + sol['data'] * r_sol['data']})
            elif voc in ['voc09', 'voc16', 'voc21', 'voc22', 'voc24']:
                [r_inc] = extract_vars(ratio_file, ['inc'])
                data.update({'data': ind['data'] * r_inc['data']})
            # elif voc in []:
            #     [r_exf, r_sol] = extract_vars(ratio_file, ['exf', 'sol'])
            #     data.update({'data': exf['data']*r_exf['data'] + sol['data']*r_sol['data']})
            elif voc in ['voc18', 'voc19', 'voc20']:
                [r_sol] = extract_vars(ratio_file, ['sol'])
                data.update({'data': sol['data'] * r_sol['data']})
            else:
                [r_inc, r_exf, r_sol] = extract_vars(ratio_file, ['inc', 'exf', 'sol'])
                data.update({'data': ind['data'] * r_inc['data'] + exf['data'] * r_exf['data'] +
                             sol['data'] * r_sol['data']})

            global_attributes = {
                'title': 'HTAPv2 inventory for the sector {0} and pollutant {1}'.format(sector, voc),
                'Conventions': 'CF-1.6',
                'institution': 'European Commission, Joint Research Centre (JRC)',
                'source': 'HTAPv2',
                'history': 'Re-writing of the HTAPv2 input to follow the CF 1.6 conventions;\n' +
                           '2017-04-28: ...',
                'references': 'publication: Janssens-Maenhout, G., et al.: HTAP_v2.2: a mosaic of regional and ' +
                              'global emission grid maps for 2008 and 2010 to study hemispheric  transport of air ' +
                              'pollution, Atmos. Chem. Phys., 15, 11411-11432,  ' +
                              'https://doi.org/10.5194/acp-15-11411-2015, 2015.\n ' +
                              'web: http://edgar.jrc.ec.europa.eu/htap_v2/index.php',
                'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                           '(Barcelona Supercomputing Center)',
            }

            out_path_aux = os.path.join(out_path, voc + '_industry')
            if not os.path.exists(out_path_aux):
                os.makedirs(out_path_aux)

            out_path_aux = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(voc, year, str(month).zfill(2)))
            print(out_path_aux)
            write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [data],
                         boundary_latitudes=create_bounds(c_lats['data']),
                         boundary_longitudes=create_bounds(c_lons['data']), global_attributes=global_attributes,)


def do_nmvoc_year_transformation(filename, out_path, sector, year):
    # TODO Documentation
    """

    :param filename:
    :param out_path:
    :param sector:
    :param year:
    :return:
    """
    import pandas as pd
    from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf
    from hermesv3_gr.tools.coordinates_tools import create_bounds

    nmvoc_ratio_file = do_ratio_list(sector)['all']
    nmvoc_ratio_list = pd.read_csv(nmvoc_ratio_file, sep=';')

    c_lats, c_lons = extract_vars(filename, ['lat', 'lon'])

    [data] = extract_vars(filename, ['emi_nmvoc'])

    for i, voc_ratio in nmvoc_ratio_list.iterrows():
        pollutant = voc_ratio['voc_group']
        ratio = voc_ratio['factor']

        data_aux = data.copy()
        data_aux['data'] = data['data'] * ratio
        data_aux['data'] = data_aux['data'].reshape((1,) + data_aux['data'].shape)
        data_aux['name'] = pollutant
        data_aux['units'] = 'kg m-2 s-1'
        global_attributes = {
            'title': 'HTAPv2 inventory for the sector {0} and pollutant {1}'.format(sector, pollutant),
            'Conventions': 'CF-1.6',
            'institution': 'European Commission, Joint Research Centre (JRC)',
            'source': 'HTAPv2',
            'history': 'Re-writing of the HTAPv2 input to follow the CF 1.6 conventions;\n' +
                       '2017-04-28: ...',
            'references': 'publication: Janssens-Maenhout, G., et al.: HTAP_v2.2: a mosaic of regional and global ' +
                          'emission grid maps for 2008 and 2010 to study hemispheric  transport of air pollution, ' +
                          'Atmos. Chem. Phys., 15, 11411-11432,  https://doi.org/10.5194/acp-15-11411-2015, 2015.\n ' +
                          'web: http://edgar.jrc.ec.europa.eu/htap_v2/index.php',
            'comment': 'Re-writing done by Carles Tena (carles.tena@bsc.es) from the BSC-CNS ' +
                       '(Barcelona Supercomputing Center)\n ' +
                       'HTAP contact: greet.maenhout@jrc.ec.europa.eu',
        }

        out_path_aux = os.path.join(out_path, pollutant + '_' + sector.lower())
        if not os.path.exists(out_path_aux):
            os.makedirs(out_path_aux)

        out_path_aux = os.path.join(out_path_aux, '{0}_{1}.nc'.format(pollutant, year))
        print(out_path_aux)
        write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [data_aux],
                     boundary_latitudes=create_bounds(c_lats['data']),
                     boundary_longitudes=create_bounds(c_lons['data']),
                     global_attributes=global_attributes,)


def get_pollutant_dict():
    # TODO Documentation
    """

    :return:
    """
    p_dict = {
        'bc': 'BC',
        'co': 'CO',
        'nh3': 'NH3',
        'nox_no2': 'NOx',
        'oc': 'OC',
        'pm10': 'PM10',
        'pm25': 'PM2.5',
        'so2': 'SO2',
        'nmvoc': 'NMVOC'
    }
    return p_dict


def get_sector_dict():
    # TODO Documentation
    """

    :return:
    """
    common_dict = {
        'month': ['ENERGY', 'INDUSTRY', 'RESIDENTIAL', 'TRANSPORT'],
        'year': ['SHIPS', 'AIR_CDS', 'AIR_CRS', 'AIR_LTO']
    }
    sector_dict = {
        'bc': common_dict,
        'co': common_dict,
        'nh3': {'month': ['AGRICULTURE', 'ENERGY', 'INDUSTRY', 'RESIDENTIAL', 'TRANSPORT'],
                'year': []},
        'nox_no2': common_dict,
        'oc': common_dict,
        'pm10': common_dict,
        'pm25': common_dict,
        'so2': common_dict,
        'nmvoc': common_dict,
    }
    return sector_dict


def get_nmvoc_sector_dict():
    # TODO Documentation
    """

    :return:
    """
    nmvoc_sectors = {'month': ['ENERGY', 'INDUSTRY_3subsectors', 'RESIDENTIAL', 'TRANSPORT'],
                     'year': ['SHIPS', 'AIR_CDS', 'AIR_CRS', 'AIR_LTO']}
    return nmvoc_sectors


def check_vocs(year):
    # TODO Documentation
    """

    :param year:
    :return:
    """
    from hermesv3_gr.tools.netcdf_tools import extract_vars
    for month in range(1, 12 + 1, 1):
        for snap in ['ENERGY', 'INDUSTRY', 'RESIDENTIAL', 'TRANSPORT']:
            nmvoc_path = os.path.join(OUTPUT_PATH, 'monthly_mean', 'nmvoc_{0}'.format(snap.lower()),
                                      'nmvoc_{0}{1}.nc'.format(year, str(month).zfill(2)))
            [new_voc] = extract_vars(nmvoc_path, ['nmvoc'])
            nmvoc_sum = new_voc['data'].sum()

            voc_sum = 0
            for voc in ['voc{0}'.format(str(x).zfill(2)) for x in range(1, 25 + 1, 1)]:
                voc_path = os.path.join(OUTPUT_PATH, 'monthly_mean', '{0}_{1}'.format(voc, snap.lower()),
                                        '{0}_{1}{2}.nc'.format(voc, year, str(month).zfill(2)))
                if os.path.exists(voc_path):
                    [new_voc] = extract_vars(voc_path, [voc])
                    voc_sum += new_voc['data'].sum()

            print('{0} month: {4}; NMVOC sum: {1}; VOCs sum: {2}; %diff: {3}'.format(
                snap, nmvoc_sum, voc_sum, 100 * (nmvoc_sum - voc_sum) / nmvoc_sum, month))


if __name__ == '__main__':
    for y in LIST_YEARS:
        for pollutant_dict in get_pollutant_dict().items():
            for current_sector in get_sector_dict()[pollutant_dict[0]]['month']:
                input_name_aux = INPUT_NAME.replace('<sector>', current_sector)
                input_name_aux = input_name_aux.replace('<year>', str(y))
                input_name_aux = input_name_aux.replace('<pollutant>', pollutant_dict[1])
                file_list = [os.path.join(INPUT_PATH, input_name_aux.replace('<month>', str(aux_month)))
                             for aux_month in range(1, 13)]

                do_transformation(file_list, os.path.join(OUTPUT_PATH, 'monthly_mean'), pollutant_dict[0],
                                  current_sector, y)
            # annual inventories
            for current_sector in get_sector_dict()[pollutant_dict[0]]['year']:
                if current_sector[0:3] == 'AIR':
                    input_name_aux = INPUT_NAME_AIR
                else:
                    input_name_aux = INPUT_NAME_SHIPS
                input_name_aux = input_name_aux.replace('<sector>', current_sector)
                input_name_aux = input_name_aux.replace('<year>', str(y))
                input_name_aux = input_name_aux.replace('<pollutant>', pollutant_dict[1])
                input_name_aux = os.path.join(INPUT_PATH, input_name_aux)

                do_transformation_annual(input_name_aux, os.path.join(OUTPUT_PATH, 'yearly_mean', ), pollutant_dict[0],
                                         current_sector, y)

        for current_sector in get_nmvoc_sector_dict()['month']:
            if current_sector == 'INDUSTRY_3subsectors':
                input_name_aux = INPUT_NAME_NMVOC_INDUSTRY
            else:
                input_name_aux = INPUT_NAME
            input_name_aux = input_name_aux.replace('<pollutant>', 'NMVOC')
            input_name_aux = input_name_aux.replace('<sector>', current_sector)
            input_name_aux = input_name_aux.replace('<year>', str(y))
            file_list = [os.path.join(INPUT_PATH, input_name_aux.replace('<month>', str(aux_month)))
                         for aux_month in range(1, 13)]

            if current_sector == 'INDUSTRY_3subsectors':
                do_nmvoc_industry_month_transformation(file_list, os.path.join(OUTPUT_PATH, 'monthly_mean'),
                                                       current_sector, y)
            else:
                do_nmvoc_month_transformation(file_list, os.path.join(OUTPUT_PATH, 'monthly_mean'), current_sector, y)
        for current_sector in get_nmvoc_sector_dict()['year']:
            if current_sector[0:3] == 'AIR':
                input_name_aux = INPUT_NAME_AIR
            else:
                input_name_aux = INPUT_NAME_SHIPS
            input_name_aux = input_name_aux.replace('<pollutant>', 'NMVOC')
            input_name_aux = input_name_aux.replace('<sector>', current_sector)
            input_name_aux = input_name_aux.replace('<year>', str(y))
            input_name_aux = os.path.join(INPUT_PATH, input_name_aux)
            print(input_name_aux)
            do_nmvoc_year_transformation(input_name_aux, os.path.join(OUTPUT_PATH, 'yearly_mean'), current_sector, y)
