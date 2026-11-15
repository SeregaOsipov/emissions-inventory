#!/usr/bin/env python

import argparse
import os
import xarray as xr
import pandas as pd
from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf, create_bounds, get_global_attributes
from preproc.preproc_utils import get_input_name
"""
downloading website: https://eccad.sedoo.fr/
reference: Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works

Run in terminal:
cd /work/mm0062/b302074/workspace/python/hermesv3_gr
cd $MY_SW/workspace/hermesv3_gr
gogomamba
mamba activate py311_hermes
python -u preproc/cams_glob_ship_v32_preproc.py >& log.cams_glob_ship_v32_preproc
"""

# ============== CONFIGURATION PARAMETERS ======================
DEFAULT_INPUT_PATH = os.environ.get('CAMS_SHIP_INPUT_PATH', '/HDD1/Data/emissions/ECCAD/CAMS-GLOB-SHIP/v3.2')
LIST_POLLUTANTS = ['NOx', 'SOx', 'EC', 'OC', 'SO4', 'CO', 'CO2', 'Ash', 'CH4']  # 'VOC_SUM': VOCs are handled separately
VERSION = 3.2

INPUT_NAME = 'CAMS-GLOB-SHIP_Glb_0.1x0.1_anthro_<pollutant>_v{}_daily.nc'.format(VERSION)


def parse_args():
    parser = argparse.ArgumentParser(description='Preprocess CAMS-GLOB-SHIP v3.2 daily emissions for HERMESv3_GR.')
    parser.add_argument('--input_path', default=DEFAULT_INPUT_PATH, help='Directory containing raw CAMS-GLOB-SHIP v3.2 NetCDF files.')
    parser.add_argument('--output_path', default=None, help='Output root directory (default: <input_path>/hermes_pp).')
    parser.add_argument('--start_date', default='2022-05-14', help='Start date YYYY-MM-DD (inclusive).')
    parser.add_argument('--end_date', default='2022-07-01', help='End date YYYY-MM-DD (inclusive).')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    INPUT_PATH = args.input_path
    OUTPUT_PATH = args.output_path or os.path.join(INPUT_PATH, 'hermes_pp')
    time_slice = slice(args.start_date, args.end_date)
    print('Applying Time Slice: {}'.format(time_slice))

    for pollutant in LIST_POLLUTANTS:
        print('Processing {}'.format(pollutant))
        emissions_file_path = get_input_name(pollutant, LIST_POLLUTANTS, INPUT_NAME, INPUT_PATH)

        if pollutant == 'Ash':
            c_lats, c_lons = extract_vars(emissions_file_path, ['latitude', 'longitude'])
        else:
            c_lats, c_lons = extract_vars(emissions_file_path, ['lat', 'lon'])

        b_lats = create_bounds(c_lats['data'])
        b_lons = create_bounds(c_lons['data'])

        global_attributes = get_global_attributes(emissions_file_path)

        print('Processing Input {}'.format(emissions_file_path))
        emissions_ds = xr.open_dataset(emissions_file_path, chunks={'time': 100})
        emissions_ds = emissions_ds.sel(time=time_slice)

        if pollutant == 'NOx':
            pollutant_name = 'nox_no'

        elif pollutant == 'VOC-SUM' or pollutant == 'VOC_SUM':
            pollutant_name = 'nmvoc'

        elif pollutant == 'SOx':
            pollutant_name = 'so2'

        else:
            pollutant_name = pollutant.lower()

        file_path = os.path.join(OUTPUT_PATH, 'daily_mean', '{0}'.format(pollutant_name))
        if not os.path.exists(file_path):
            os.makedirs(file_path, exist_ok=True)

        daily_dates = emissions_ds.time

        for date, i in zip(daily_dates, range(daily_dates.size)):
            print('Date {} out of {}: {}'.format(i, daily_dates.size, date.values))

            data = emissions_ds.shipping.isel(time=i).load()

            emission = {
                'name': pollutant_name,
                'units': 'kg.m-2.s-1',
                'data': data.data.reshape((1, data.shape[-2], data.shape[-1]))
            }

            write_netcdf(
                os.path.join(file_path, '{0}_{1}.nc'.format(pollutant_name, date.dt.strftime('%Y%m%d').item())),
                c_lats['data'], c_lons['data'], [emission], date=pd.to_datetime(date.values),
                boundary_latitudes=b_lats, boundary_longitudes=b_lons, global_attributes=global_attributes)

print('DONE')