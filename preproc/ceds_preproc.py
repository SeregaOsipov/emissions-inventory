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

# ============== README ======================
"""
downloading website: http://www.globalchange.umd.edu/ceds/ceds-cmip6-data/
reference: https://www.geosci-model-dev.net/11/369/2018/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/esarchive/recon/jgcri/ceds/original_files'
OUTPUT_PATH = '/esarchive/recon/jgcri/ceds'
LIST_POLLUTANTS = ['BC', 'CO', 'NH3', 'NMVOC', 'NOx', 'OC', 'SO2']
VOC_POLLUTANTS = ['VOC01', 'VOC02', 'VOC03', 'VOC04', 'VOC05', 'VOC06', 'VOC07', 'VOC08', 'VOC09', 'VOC12', 'VOC13',
                  'VOC14', 'VOC15', 'VOC16', 'VOC17', 'VOC18', 'VOC19', 'VOC20', 'VOC21', 'VOC22', 'VOC23', 'VOC24',
                  'VOC25']

LIST_SECTORS = ['agriculture', 'energy', 'industry', 'transport', 'residential', 'solvents', 'waste', 'ships']
# LIST_YEARS = from 1950 to 2014
LIST_YEARS = [2014]
INPUT_NAME = '<pollutant>-em-anthro_input4MIPs_emissions_CMIP_CEDS-v2016-07-26-sectorDim_gr_<st_year>01-<en_year>12.nc'
VOC_INPUT_NAME = '<voc_name>-em-speciated-VOC_input4MIPs_emissions_CMIP_CEDS-v2016-07-26-sector' + \
                 'Dim-supplemental-data_gr_<st_year>01-<en_year>12.nc'
DO_AIR = True
AIR_INPUT_NAME = '<pollutant>-em-AIR-anthro_input4MIPs_emissions_CMIP_CEDS-v2016-07-26_gr_<st_year>01-<en_year>12.nc'
# ==============================================================


def voc_to_vocname(voc):
    """
    Gets the voc complete name from the VOCXX format

    :param voc: Voc number in the format VOCXX
    :type voc: str

    :return: Voc name
    :rtype:str
    """
    voc_dict = {
        'VOC01': 'alcohols',
        'VOC02': 'ethane',
        'VOC03': 'propane',
        'VOC04': 'butanes',
        'VOC05': 'pentanes',
        'VOC06': 'hexanes-pl',
        'VOC07': 'ethene',
        'VOC08': 'propene',
        'VOC09': 'ethyne',
        'VOC12': 'other-alke',
        'VOC13': 'benzene',
        'VOC14': 'toluene',
        'VOC15': 'xylene',
        'VOC16': 'trimethylb',
        'VOC17': 'other-arom',
        'VOC18': 'esters',
        'VOC19': 'ethers',
        'VOC20': 'chlorinate',
        'VOC21': 'methanal',
        'VOC22': 'other-alka',
        'VOC23': 'ketones',
        'VOC24': 'acids',
        'VOC25': 'other-voc'
    }

    return voc_dict[voc]


def sector_to_index(sector):
    """
    Gets the index where are allocated the emissions for the selected sector.

    :param sector: Name to the sector to get the index position.
    :type sector: str

    :return: Index of the position of the current sector
    :rtype: int
    """
    sector_dict = {
        'agriculture': 0,
        'energy': 1,
        'industry': 2,
        'transport': 3,
        'residential': 4,
        'solvents': 5,
        'waste': 6,
        'ships': 7
    }

    return sector_dict[sector]


def get_input_name(pollutant, year, air=False):
    """
    Gets the path for the input file name

    :param pollutant: Name of the pollutant
    :type pollutant: str

    :param year: Year to extract
    :type year: int

    :param air: Indicates if the input file is related with air emissions
    :type air: bool

    :return: Path to the input file
    :rtype: str
    """
    if air:
        file_name = AIR_INPUT_NAME.replace('<pollutant>', pollutant)
    elif pollutant in LIST_POLLUTANTS:
        file_name = INPUT_NAME.replace('<pollutant>', pollutant)
    elif pollutant in VOC_POLLUTANTS:
        file_name = VOC_INPUT_NAME.replace('<voc_name>', '{0}-{1}'.format(pollutant, voc_to_vocname(pollutant)))
    else:
        raise ValueError('Pollutant {0} not in pollutant list or voc list'.format(pollutant))

    if year < 1851 or year > 2014:
        raise ValueError('Select a year between 1851 and 2014')
    elif year <= 1899:
        file_name = file_name.replace('<st_year>', str(1851)).replace('<en_year>', str(1899))
    elif year <= 1949:
        file_name = file_name.replace('<st_year>', str(1900)).replace('<en_year>', str(1949))
    elif year <= 1949:
        file_name = file_name.replace('<st_year>', str(1950)).replace('<en_year>', str(1999))
    else:
        file_name = file_name.replace('<st_year>', str(2000)).replace('<en_year>', str(2014))

    return os.path.join(INPUT_PATH, file_name)


def get_full_year_data(file_name, pollutant, sector, year, air=False):
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

    :param air: Indicates if the input file is related with air emissions
    :type air: bool

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
    if air:
        data = nc.variables['AIR'][i_time:i_time + 12, :, :, :]
    elif pollutant in LIST_POLLUTANTS:
        data = nc.variables['{0}_em_anthro'.format(pollutant)][i_time:i_time+12, sector_to_index(sector), :, :]
    elif pollutant in VOC_POLLUTANTS:
        data = nc.variables['{0}-{1}_em_speciated_VOC'.format(
            pollutant, voc_to_vocname(pollutant).replace('-', '_'))][i_time:i_time+12, sector_to_index(sector), :, :]
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


def do_transformation(year):
    """
    Does the transformation for the selected year

    :param year: Year to calculate
    :type year: int
    """
    from datetime import datetime
    from hermesv3_gr.tools.netcdf_tools import extract_vars, get_grid_area, write_netcdf
    for pollutant in LIST_POLLUTANTS + VOC_POLLUTANTS:
        file_name = get_input_name(pollutant, year)
        if os.path.exists(file_name):
            c_lats, c_lons, b_lats, b_lons = extract_vars(file_name, ['lat', 'lon', 'lat_bnds', 'lon_bnds'])
            cell_area = get_grid_area(file_name)

            global_attributes = get_global_attributes(file_name)
            for sector in LIST_SECTORS:
                data = get_full_year_data(file_name, pollutant, sector, year)

                if pollutant == 'NOx':
                    pollutant_name = 'nox_no2'
                else:
                    pollutant_name = pollutant.lower()

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
                        boundary_latitudes=b_lats['data'], boundary_longitudes=b_lons['data'], cell_area=cell_area,
                        global_attributes=global_attributes)
        else:
            raise IOError('File not found {0}'.format(file_name))
    return True


def do_air_transformation(year):
    """
    Does the transformations of the ari emissions for the selected year.

    :param year: Year to calculate
    :type year: int
    """
    from datetime import datetime
    from hermesv3_gr.tools.netcdf_tools import extract_vars, get_grid_area, write_netcdf

    for pollutant in LIST_POLLUTANTS:
        file_name = get_input_name(pollutant, year, air=True)
        if os.path.exists(file_name):
            c_lats, c_lons, b_lats, b_lons = extract_vars(file_name, ['lat', 'lon', 'lat_bnds', 'lon_bnds'])
            cell_area = get_grid_area(file_name)

            global_attributes = get_global_attributes(file_name)

            data = get_full_year_data(file_name, pollutant, '', year, air=True)

            if pollutant == 'NOx':
                pollutant_name = 'nox_no2'
            else:
                pollutant_name = pollutant.lower()

            for sector in ['air_lto', 'air_cds', 'air_crs']:
                file_path = os.path.join(OUTPUT_PATH, 'monthly_mean', '{0}_{1}'.format(pollutant_name, sector))
                if not os.path.exists(file_path):
                    os.makedirs(file_path)

                if sector == 'air_lto':
                    data_aux = data[:, 0:1 + 1, :, :].sum(axis=1)
                elif sector == 'air_cds':
                    data_aux = data[:, 2:14 + 1, :, :].sum(axis=1)
                elif sector == 'air_crs':
                    data_aux = data[:, 15:24 + 1, :, :].sum(axis=1)
                else:
                    print('ERROR')
                    sys.exit(1)

                for month in range(1, 12 + 1, 1):
                    emission = {
                        'name': pollutant_name,
                        'units': 'kg.m-2.s-1',
                        'data': data_aux[month - 1, :, :].reshape((1,) + cell_area.shape)
                    }
                    write_netcdf(
                        os.path.join(file_path, '{0}_{1}{2}.nc'.format(pollutant_name, year, str(month).zfill(2))),
                        c_lats['data'], c_lons['data'], [emission], date=datetime(year=year, month=month, day=1),
                        boundary_latitudes=b_lats['data'], boundary_longitudes=b_lons['data'], cell_area=cell_area,
                        global_attributes=global_attributes)
        else:
            raise IOError('File not found {0}'.format(file_name))
    return True


if __name__ == '__main__':
    for y in LIST_YEARS:
        # do_transformation(y)
        if DO_AIR:
            do_air_transformation(y)
