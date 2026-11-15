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


import sys
import os


# ============== CONFIGURATION PARAMETERS ======================
OUTPUT_PATH = '/esarchive/recon/ecmwf/cams81/original_files/cams_reg_apv221/pm'
WORLD_INFO_PATH = '/home/Earth/ctena/Models/HERMESv3/IN/data/profiles/temporal/tz_world_country_iso3166.csv'
TNO_WORLD_MASK = '/esarchive/recon/ecmwf/cams81/original_files/cams_reg_apv221/CAMS-REG-AP_v2_WorldMask.nc'
CSV_PATH = '/esarchive/recon/ecmwf/cams81/original_files/cams_reg_apv221/PM_split_for_CAMS-REG-v2_2.csv'
YEAR = 2015
# ==============================================================


def extract_vars(netcdf_path, variables_list, attributes_list=()):
    # TODO Docuemtnation
    """

    :param netcdf_path:
    :param variables_list:
    :param attributes_list:
    :return:
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

    print(data_list)

    return data_list


def write_netcdf(netcdf_path, center_latitudes, center_longitudes, data_list,
                 levels=None, date=None, hours=None,
                 boundary_latitudes=None, boundary_longitudes=None, cell_area=None, global_attributes=None,
                 regular_latlon=False,
                 rotated=False, rotated_lats=None, rotated_lons=None, north_pole_lat=None, north_pole_lon=None,
                 lcc=False, lcc_x=None, lcc_y=None, lat_1_2=None, lon_0=None, lat_0=None):
    # TODO Docuemtnation
    """

    :param netcdf_path:
    :param center_latitudes:
    :param center_longitudes:
    :param data_list:
    :param levels:
    :param date:
    :param hours:
    :param boundary_latitudes:
    :param boundary_longitudes:
    :param cell_area:
    :param global_attributes:
    :param regular_latlon:
    :param rotated:
    :param rotated_lats:
    :param rotated_lons:
    :param north_pole_lat:
    :param north_pole_lon:
    :param lcc:
    :param lcc_x:
    :param lcc_y:
    :param lat_1_2:
    :param lon_0:
    :param lat_0:
    :return:
    """
    from cf_units import Unit, encode_time
    from netCDF4 import Dataset

    if not (regular_latlon or lcc or rotated):
        regular_latlon = True
    print(netcdf_path)
    netcdf = Dataset(netcdf_path, mode='w', format="NETCDF4")

    # ===== Dimensions =====
    if regular_latlon:
        var_dim = ('lat', 'lon',)

        # Latitude
        if len(center_latitudes.shape) == 1:
            netcdf.createDimension('lat', center_latitudes.shape[0])
            lat_dim = ('lat',)
        elif len(center_latitudes.shape) == 2:
            netcdf.createDimension('lat', center_latitudes.shape[0])
            lat_dim = ('lon', 'lat',)
        else:
            print('ERROR: Latitudes must be on a 1D or 2D array instead of {0}'.format(len(center_latitudes.shape)))
            sys.exit(1)

        # Longitude
        if len(center_longitudes.shape) == 1:
            netcdf.createDimension('lon', center_longitudes.shape[0])
            lon_dim = ('lon',)
        elif len(center_longitudes.shape) == 2:
            netcdf.createDimension('lon', center_longitudes.shape[1])
            lon_dim = ('lon', 'lat',)
        else:
            print('ERROR: Longitudes must be on a 1D or 2D array instead of {0}'.format(len(center_longitudes.shape)))
            sys.exit(1)
    elif rotated:
        var_dim = ('rlat', 'rlon',)

        # Rotated Latitude
        if rotated_lats is None:
            print('ERROR: For rotated grids is needed the rotated latitudes.')
            sys.exit(1)
        netcdf.createDimension('rlat', len(rotated_lats))
        lat_dim = ('rlat', 'rlon',)

        # Rotated Longitude
        if rotated_lons is None:
            print('ERROR: For rotated grids is needed the rotated longitudes.')
            sys.exit(1)
        netcdf.createDimension('rlon', len(rotated_lons))
        lon_dim = ('rlat', 'rlon',)

    elif lcc:
        var_dim = ('y', 'x',)

        netcdf.createDimension('y', len(lcc_y))
        lat_dim = ('y', 'x',)

        netcdf.createDimension('x', len(lcc_x))
        lon_dim = ('y', 'x',)
    else:
        lat_dim = None
        lon_dim = None
        var_dim = None

    # Levels
    if levels is not None:
        netcdf.createDimension('lev', len(levels))

    # Bounds
    if boundary_latitudes is not None:
        # print boundary_latitudes.shape
        # print len(boundary_latitudes[0, 0])
        netcdf.createDimension('nv', len(boundary_latitudes[0, 0]))
        # sys.exit()

    # Time
    netcdf.createDimension('time', None)

    # ===== Variables =====
    # Time
    if date is None:
        time = netcdf.createVariable('time', 'd', ('time',), zlib=True)
        time.units = "months since 2000-01-01 00:00:00"
        time.standard_name = "time"
        time.calendar = "gregorian"
        time.long_name = "time"
        time[:] = [0.]
    else:
        time = netcdf.createVariable('time', 'd', ('time',), zlib=True)
        u = Unit('hours')
        # print u.offset_by_time(encode_time(date.year, date.month, date.day, date.hour, date.minute, date.second))
        # Unit('hour since 1970-01-01 00:00:00.0000000 UTC')
        time.units = str(
            u.offset_by_time(encode_time(date.year, date.month, date.day, date.hour, date.minute, date.second)))
        time.standard_name = "time"
        time.calendar = "gregorian"
        time.long_name = "time"
        time[:] = hours

    # Latitude
    lats = netcdf.createVariable('lat', 'f', lat_dim, zlib=True)
    lats.units = "degrees_north"
    lats.axis = "Y"
    lats.long_name = "latitude coordinate"
    lats.standard_name = "latitude"
    lats[:] = center_latitudes

    if boundary_latitudes is not None:
        lats.bounds = "lat_bnds"
        lat_bnds = netcdf.createVariable('lat_bnds', 'f', lat_dim + ('nv',), zlib=True)
        # print lat_bnds[:].shape, boundary_latitudes.shape
        lat_bnds[:] = boundary_latitudes

    # Longitude
    lons = netcdf.createVariable('lon', 'f', lon_dim, zlib=True)

    lons.units = "degrees_east"
    lons.axis = "X"
    lons.long_name = "longitude coordinate"
    lons.standard_name = "longitude"
    print('lons:', lons[:].shape, center_longitudes.shape)
    lons[:] = center_longitudes
    if boundary_longitudes is not None:
        lons.bounds = "lon_bnds"
        lon_bnds = netcdf.createVariable('lon_bnds', 'f', lon_dim + ('nv',), zlib=True)
        # print lon_bnds[:].shape, boundary_longitudes.shape
        lon_bnds[:] = boundary_longitudes

    if rotated:
        # Rotated Latitude
        rlat = netcdf.createVariable('rlat', 'f', ('rlat',), zlib=True)
        rlat.long_name = "latitude in rotated pole grid"
        rlat.units = Unit("degrees").symbol
        rlat.standard_name = "grid_latitude"
        rlat[:] = rotated_lats

        # Rotated Longitude
        rlon = netcdf.createVariable('rlon', 'f', ('rlon',), zlib=True)
        rlon.long_name = "longitude in rotated pole grid"
        rlon.units = Unit("degrees").symbol
        rlon.standard_name = "grid_longitude"
        rlon[:] = rotated_lons
    if lcc:
        x = netcdf.createVariable('x', 'd', ('x',), zlib=True)
        x.units = Unit("km").symbol
        x.long_name = "x coordinate of projection"
        x.standard_name = "projection_x_coordinate"
        x[:] = lcc_x

        y = netcdf.createVariable('y', 'd', ('y',), zlib=True)
        y.units = Unit("km").symbol
        y.long_name = "y coordinate of projection"
        y.standard_name = "projection_y_coordinate"
        y[:] = lcc_y

    cell_area_dim = var_dim
    # Levels
    if levels is not None:
        var_dim = ('lev',) + var_dim
        lev = netcdf.createVariable('lev', 'f', ('lev',), zlib=True)
        lev.units = Unit("m").symbol
        lev.positive = 'up'
        lev[:] = levels

    # All variables
    if len(data_list) is 0:
        var = netcdf.createVariable('aux_var', 'f', ('time',) + var_dim, zlib=True)
        var[:] = 0
    for variable in data_list:
        # print ('time',) + var_dim
        var = netcdf.createVariable(variable['name'], 'f', ('time',) + var_dim, zlib=True)
        var.units = Unit(variable['units']).symbol
        if 'long_name' in variable:
            var.long_name = str(variable['long_name'])
        if 'standard_name' in variable:
            var.standard_name = str(variable['standard_name'])
        if 'cell_method' in variable:
            var.cell_method = str(variable['cell_method'])
        var.coordinates = "lat lon"
        if cell_area is not None:
            var.cell_measures = 'area: cell_area'
        if regular_latlon:
            var.grid_mapping = 'crs'
        elif rotated:
            var.grid_mapping = 'rotated_pole'
        elif lcc:
            var.grid_mapping = 'Lambert_conformal'
        # if variable['data'] is not 0:
        #     print var[:].shape, variable['data'].shape
        try:
            var[:] = variable['data']
        except Exception:
            print('VAR ERROR, netcdf shape: {0}, variable shape: {1}'.format(var[:].shape, variable['data'].shape))

    # Grid mapping
    if regular_latlon:
        # CRS
        mapping = netcdf.createVariable('crs', 'i')
        mapping.grid_mapping_name = "latitude_longitude"
        mapping.semi_major_axis = 6371000.0
        mapping.inverse_flattening = 0
    elif rotated:
        # Rotated pole
        mapping = netcdf.createVariable('rotated_pole', 'c')
        mapping.grid_mapping_name = 'rotated_latitude_longitude'
        mapping.grid_north_pole_latitude = north_pole_lat
        mapping.grid_north_pole_longitude = north_pole_lon
    elif lcc:
        # CRS
        mapping = netcdf.createVariable('Lambert_conformal', 'i')
        mapping.grid_mapping_name = "lambert_conformal_conic"
        mapping.standard_parallel = lat_1_2
        mapping.longitude_of_central_meridian = lon_0
        mapping.latitude_of_projection_origin = lat_0

    # Cell area
    if cell_area is not None:
        c_area = netcdf.createVariable('cell_area', 'f', cell_area_dim)
        c_area.long_name = "area of the grid cell"
        c_area.standard_name = "cell_area"
        c_area.units = Unit("m2").symbol
        # print c_area[:].shape, cell_area.shape
        c_area[:] = cell_area

    if global_attributes is not None:
        netcdf.setncatts(global_attributes)

    netcdf.close()
    return True


def get_grid_area(filename):
    """
    Calculate the area of each cell.

    :param filename: Full path to the NetCDF to calculate the cell areas.
    :type filename: str

    :return: Returns the area of each cell.
    :rtype: numpy.array
    """
    from cdo import Cdo
    from netCDF4 import Dataset

    cdo = Cdo()
    src = cdo.gridarea(input=filename)
    nc_aux = Dataset(src, mode='r')
    grid_area = nc_aux.variables['cell_area'][:]
    nc_aux.close()

    return grid_area


def create_bounds(coords, number_vertices=2):
    """
    Calculate the vertices coordinates.

    :param coords: Coordinates in degrees (latitude or longitude)
    :type coords: numpy.array

    :param number_vertices: Non mandatory parameter that informs the number of vertices that must have the boundaries.
            (by default 2)
    :type number_vertices: int

    :return: Array with as many elements as vertices for each value of coords.
    :rtype: numpy.array
    """
    import numpy as np

    interval = coords[1] - coords[0]

    coords_left = coords - interval / 2
    coords_right = coords + interval / 2
    if number_vertices == 2:
        bound_coords = np.dstack((coords_left, coords_right))
    elif number_vertices == 4:
        bound_coords = np.dstack((coords_left, coords_right, coords_right, coords_left))
    else:
        raise ValueError('The number of vertices of the boudaries must be 2 or 4')

    return bound_coords


def create_pm_ratio(pm):
    # TODO Documentation
    """

    :param pm:
    :return:
    """
    import numpy as np
    [country_values, lat, lon] = extract_vars(TNO_WORLD_MASK, ['timezone_id', 'lat', 'lon'])
    country_values = country_values['data'].reshape((country_values['data'].shape[1], country_values['data'].shape[1]))
    print(country_values)
    #sys.exit()

    print(OUTPUT_PATH)
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)

    complete_output_path = os.path.join(OUTPUT_PATH, 'ratio_{0}_{1}.nc'.format(pm, YEAR))
    if not os.path.exists(complete_output_path):
        print('Creating ratio file for {0}\npath: {1}'.format(pm, complete_output_path))
        data_list = []
        for gnfr in get_sector_list(pm):
            print(gnfr)
            mask_factor = np.zeros(country_values.shape)
            iso_codes = get_iso_codes()
            for country_code, factor in get_country_code_and_factor(pm, gnfr, YEAR).items():
                try:
                    mask_factor[country_values == iso_codes[country_code]] = factor
                except Exception:
                    pass
            # To fulfill the blanks on the map
            mask_factor[mask_factor <= 0] = get_default_ratio(pm, gnfr, YEAR)

            data_list.append({
                'name': 'gnfr_{0}'.format(gnfr),
                'units': '',
                'data': mask_factor.reshape((1,) + mask_factor.shape)
            })
        write_netcdf(complete_output_path, lat['data'], lon['data'], data_list)
    else:
        print('Ratio file for {0} already created\npath: {1}'.format(pm, complete_output_path))
    return True


def get_default_ratio(pm, gnfr, YEAR):
    # TODO Documentation
    """

    :param pm:
    :param gnfr:
    :return:
    """
    import pandas as pd

    df = pd.read_csv(CSV_PATH, sep=',')

    df = df[df.year == YEAR]
    df = df.loc[df['pmcode'] == pm, :]
    df = df.loc[df['gnfr'] == gnfr, :]

    return df.loc[df['ISO3'] == 'EUR', 'fr'].item()


def get_iso_codes():
    # TODO Documentation
    """

    :return:
    """
    import pandas as pd

    # df = pd.read_csv(self.world_info, sep=';', index_col=False, names=["country", "country_code"])
    df = pd.read_csv(WORLD_INFO_PATH, sep=';')
    del df['time_zone'], df['time_zone_code']
    df = df.drop_duplicates().dropna()
    df = df.set_index('country_code_alpha')
    codes_dict = df.to_dict()
    codes_dict = codes_dict['country_code']

    return codes_dict


def get_pm_list():
    # TODO Documentation
    """

    :return:
    """
    import pandas as pd

    df = pd.read_csv(CSV_PATH, sep=',')
    del df['ISO3'], df['gnfr'], df['fr'], df['year']
    df = df.drop_duplicates().dropna()
    pm_list = df.pmcode.values
    print(df.pmcode.values)
    return df.pmcode.values


def get_sector_list(pm):
    # TODO Documentation
    """

    :param pm:
    :return:
    """
    import pandas as pd
    df = pd.read_csv(CSV_PATH, sep=',')
    # Shipping emissions speciated in a common profile (sea area)
    # df = df[df.gnfr != 'G']
    df = df[df.pmcode == pm]
    del df['ISO3'], df['pmcode'], df['year'], df['fr']
    df = df.drop_duplicates().dropna()
    print(df.gnfr.values)
    return df.gnfr.values


def get_sector_list_text(voc):
    # TODO Documentation
    """

    :param voc:
    :return:
    """
    voc = voc.replace('voc', 'v')
    sector_list = get_sector_list(voc)
    new_list = []
    for int_sector in sector_list:
        new_list.append('gnfr_{0}'.format(int_sector))
    return new_list


def get_country_code_and_factor(pm, gnfr, YEAR):
    # TODO Documentation
    """

    :param pm:
    :param gnfr:
    :param YEAR:
    :return:
    """
    import pandas as pd
    df = pd.read_csv(CSV_PATH, sep=',')
    df = df[df.year == YEAR]
    df = df[df.pmcode == pm]
    df = df[df.gnfr == gnfr]
    del df['gnfr'], df['pmcode'], df['year']
    df = df.drop_duplicates().dropna()
    df = df.set_index('ISO3')

    country_dict = df.to_dict()
    country_dict = country_dict['fr']

    return country_dict


if __name__ == '__main__':
    for pm_name in get_pm_list():
        create_pm_ratio(pm_name)
