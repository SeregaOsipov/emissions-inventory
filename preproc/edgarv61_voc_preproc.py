#!/usr/bin/env python

%load_ext autoreload
%autoreload 2

import os
import subprocess
from netCDF4 import Dataset
import xarray as xr
import numpy as np
from warnings import warn as warning

from preproc.preproc_utils import ipcc_to_sector_dict, get_grid_area, write_netcdf, EDGAR_EIGHT_SECTORS

# ============== README ======================
"""
website: https://edgar.jrc.ec.europa.eu/dataset_ap81_VOC_spec
downloading website: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v81_FT2022_VOC_spec/

Run in terminal:
cd /work/mm0062/b302074/workspace/python/hermesv3_gr
gogomamba
mamba activate py311_hermes
python -u preproc/edgar_v81_voc_preproc.py >& log.edgar_v81_voc_preproc
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/project/k10048/osipovs/Data/emissions/EDGAR/v81_FT2022_AP_new/'
OUTPUT_PATH = INPUT_PATH + '/hermes_pp/'
LIST_POLLUTANTS = ['voc1', 'voc2', 'voc3', 'voc4', 'voc5', 'voc6', 'voc7', 'voc8', 'voc9', 'voc10', 'voc11', 'voc12',
                   'voc13', 'voc14', 'voc15', 'voc16', 'voc17', 'voc18', 'voc19', 'voc20', 'voc21', 'voc22', 'voc23',
                   'voc24', 'voc25']
LIST_YEARS = [2017,]

# To do yearly emissions
PROCESS_YEARLY = True
YEARLY_INPUT_NAME = 'yearly/v432_VOC_spec_<pollutant>_<year>_<ipcc>.0.1x0.1.nc'

# To process monthly emissions, 2010 directly from monthly_input_name and other years calculated using monthly gridded factors derived from the 2010 monthly data
PROCESS_MONTHLY = False
MONTHLY_INPUT_NAME = 'monthly/v432_VOC_spec_<pollutant>_2010_<month>_<ipcc>.0.1x0.1.nc'
MONTHLY_PATTERN_FILE = 'temporal_profiles/v432_FM_<sector>.0.1x0.1.nc'
# ==============================================================


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
            file_path = os.path.join(INPUT_PATH, YEARLY_INPUT_NAME.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<ipcc>',ipcc))

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
