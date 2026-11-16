#!/usr/bin/env python

import argparse
import concurrent.futures
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
    parser.add_argument('--pollutants', nargs='+', default=LIST_POLLUTANTS, help='Subset of pollutants to process.')
    parser.add_argument('--workers', type=int, default=8, help='Parallel worker processes across pollutants.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing daily NetCDF files.')
    return parser.parse_args()


def _process_pollutant(task):
    pollutant, input_path, output_path, start_date, end_date, overwrite = task
    time_slice = slice(start_date, end_date)
    print('Processing {}'.format(pollutant), flush=True)
    emissions_file_path = get_input_name(pollutant, LIST_POLLUTANTS, INPUT_NAME, input_path)

    if pollutant == 'Ash':
        c_lats, c_lons = extract_vars(emissions_file_path, ['latitude', 'longitude'])
    else:
        c_lats, c_lons = extract_vars(emissions_file_path, ['lat', 'lon'])

    b_lats = create_bounds(c_lats['data'])
    b_lons = create_bounds(c_lons['data'])
    global_attributes = get_global_attributes(emissions_file_path)

    print('Processing Input {}'.format(emissions_file_path), flush=True)
    emissions_ds = xr.open_dataset(emissions_file_path, chunks={'time': 100}).sel(time=time_slice)

    if pollutant == 'NOx':
        pollutant_name = 'nox_no'
    elif pollutant in ('VOC-SUM', 'VOC_SUM'):
        pollutant_name = 'nmvoc'
    elif pollutant == 'SOx':
        pollutant_name = 'so2'
    else:
        pollutant_name = pollutant.lower()

    file_path = os.path.join(output_path, 'daily_mean', pollutant_name)
    os.makedirs(file_path, exist_ok=True)

    daily_dates = emissions_ds.time
    written = 0
    for i, date in enumerate(daily_dates):
        out_nc = os.path.join(file_path, '{0}_{1}.nc'.format(pollutant_name, date.dt.strftime('%Y%m%d').item()))
        if not overwrite and os.path.isfile(out_nc) and os.path.getsize(out_nc) > 0:
            continue

        print('[{}] Date {} out of {}: {}'.format(pollutant_name, i, daily_dates.size, date.values), flush=True)
        data = emissions_ds.shipping.isel(time=i).load()
        emission = {
            'name': pollutant_name,
            'units': 'kg.m-2.s-1',
            'data': data.data.reshape((1, data.shape[-2], data.shape[-1])),
        }

        tmp_nc = '{0}.tmp.{1}'.format(out_nc, os.getpid())
        try:
            write_netcdf(
                tmp_nc,
                c_lats['data'], c_lons['data'], [emission], date=pd.to_datetime(date.values),
                boundary_latitudes=b_lats, boundary_longitudes=b_lons, global_attributes=global_attributes,
            )
            os.replace(tmp_nc, out_nc)
        finally:
            if os.path.exists(tmp_nc):
                os.remove(tmp_nc)
        written += 1

    emissions_ds.close()
    print('Finished {} (wrote {} files)'.format(pollutant_name, written), flush=True)
    return pollutant_name, written


if __name__ == '__main__':
    args = parse_args()
    INPUT_PATH = args.input_path
    OUTPUT_PATH = args.output_path or os.path.join(INPUT_PATH, 'hermes_pp')
    print('Applying Time Slice: slice({!r}, {!r}) with {} worker(s)'.format(args.start_date, args.end_date, args.workers), flush=True)

    tasks = [
        (p, INPUT_PATH, OUTPUT_PATH, args.start_date, args.end_date, args.overwrite)
        for p in args.pollutants
    ]
    if args.workers <= 1 or len(tasks) <= 1:
        for t in tasks:
            _process_pollutant(t)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(args.workers, len(tasks))) as executor:
            list(executor.map(_process_pollutant, tasks))

    print('DONE', flush=True)