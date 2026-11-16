#!/usr/bin/env python

import argparse
import os
import sys
import numpy as np
import xarray as xr
import pandas as pd
from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf  # get_grid_area
# ============== README ======================
"""
The script speciates shipping VOC emissions. 

downloading website: https://eccad.sedoo.fr/
reference: Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works

Run in terminal on Levante:
s2n -p compute
cd /work/mm0062/b302074/workspace/python/hermesv3_gr
gogomamba
mamba activate py311_hermes
python -u preproc/cams_glob_ship_v32_voc_preproc.py >& log.cams_glob_ship_v32_voc_preproc

Run in terminal on Shaheen:
salloc --partition=shared -n 8 -c 1 --time=8:00:00
ssh node
cd /scratch/osipovs/iops/sw/workspace/hermesv3_gr
source /project/k10066/osipovs/.commonrc; gogomamba; mamba activate py311_hermes
python -u preproc/cams_glob_ship_v32_voc_preproc.py >& log.cams_glob_ship_v32_voc_preproc
"""

# ============== CONFIGURATION PARAMETERS ======================
DEFAULT_SPECIATION_PATH = os.environ.get(
    'HTAP_VOC_SPECIATION_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nmvoc', 'NMVOC_speciation_HTAP_v3.xls'),
)
DEFAULT_INPUT_PATH = os.environ.get('CAMS_SHIP_INPUT_PATH', '/HDD1/Data/emissions/ECCAD/CAMS-GLOB-SHIP/v3.2')

# Common
VERSION = 3.2
INPUT_NAME = 'CAMS-GLOB-SHIP_Glb_0.1x0.1_anthro_<pollutant>_v{}_daily.nc'.format(VERSION)


def parse_args():
    parser = argparse.ArgumentParser(description='Speciate CAMS-GLOB-SHIP v3.2 VOC daily emissions for HERMESv3_GR.')
    parser.add_argument('--input_path', default=DEFAULT_INPUT_PATH, help='Directory containing raw CAMS-GLOB-SHIP v3.2 NetCDF files.')
    parser.add_argument('--output_path', default=None, help='Output root directory (default: <input_path>/hermes_pp).')
    parser.add_argument('--speciation_path', default=DEFAULT_SPECIATION_PATH, help='Path to NMVOC_speciation_HTAP_v3.xls.')
    parser.add_argument('--start_date', default='2022-05-14', help='Start date YYYY-MM-DD (inclusive).')
    parser.add_argument('--end_date', default='2022-07-01', help='End date YYYY-MM-DD (inclusive).')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing daily VOC NetCDF files.')
    return parser.parse_args()


def create_bounds(coordinates, number_vertices=2):
    """
    Calculate the vertices coordinates.

    :param coordinates: Coordinates in degrees (latitude or longitude)
    :type coordinates: numpy.array

    :param number_vertices: Non mandatory parameter that informs the number of vertices that must have the boundaries.
            (by default 2)
    :type number_vertices: int

    :return: Array with as many elements as vertices for each value of coords.
    :rtype: numpy.array
    """
    interval = coordinates[1] - coordinates[0]

    coords_left = coordinates - interval / 2
    coords_right = coordinates + interval / 2
    if number_vertices == 2:
        bound_coords = np.dstack((coords_left, coords_right))
    elif number_vertices == 4:
        bound_coords = np.dstack((coords_left, coords_right, coords_right, coords_left))
    else:
        raise ValueError('The number of vertices of the boudaries must be 2 or 4')

    return bound_coords


if __name__ == '__main__':
    args = parse_args()
    HTAP_v3_VOC_SPECIATION_PATH = args.speciation_path
    INPUT_PATH = args.input_path
    OUTPUT_PATH = args.output_path or os.path.join(INPUT_PATH, 'hermes_pp')
    time_slice = slice(args.start_date, args.end_date)
    print('Applying Time Slice: {}'.format(time_slice))
    output_folder_path = os.path.join(OUTPUT_PATH, 'daily_mean')
    print('Saving output to {}'.format(output_folder_path))

    input_name_aux = INPUT_NAME
    input_name_aux = input_name_aux.replace('<pollutant>', 'VOC_SUM')
    # input_name_aux = input_name_aux.replace('<year>', str(year))  # 1 file for all years
    emissions_file_path = os.path.join(INPUT_PATH, input_name_aux)
    print('Processing Input {}'.format(emissions_file_path))
    emissions_ds = xr.open_dataset(emissions_file_path, chunks={'time':100})
    emissions_ds = emissions_ds.sel(time=time_slice)
    # emissions_ds = emissions_ds.load()  # if memory allows , read it all to speed up

    c_lats, c_lons = extract_vars(emissions_file_path, ['lat', 'lon'])

    # get the VOC speciation for shipping
    voc_speciation_df = pd.read_excel(HTAP_v3_VOC_SPECIATION_PATH, skiprows=2)  # , header=)
    vocs = voc_speciation_df.filter(regex=("voc.*")).columns.to_list()

    df = voc_speciation_df
    speciation_df = df.loc[df['SECTOR NAME'].isin(['International shipping'])].reset_index()[vocs]
    speciation_ds = speciation_df.transpose().rename({0: 'voc_speciation'}, axis='columns').to_xarray()
    speciation_ds = speciation_ds.rename({'index': 'voc'})

    speciated_vocs_ds = speciation_ds.voc_speciation * emissions_ds['shipping']

    global_attributes = {
        'title': 'CAMS Glob Ship v3.2 inventory, NMVOC speciated using profile from HTAPv3 for international shipping',
        'Conventions': 'CF-1.6',
        'source': 'CAMS Glob Ship v3.2',
        'comment': 'Re-writing done by Sergey Osipov (sergey.osipvo@kaust.edu.sa)',
    }

    daily_dates = emissions_ds.time

    for date, i in zip(daily_dates, range(daily_dates.size)):
        date_compact = date.dt.strftime('%Y%m%d').item()
        pending_vocs = []
        for voc in vocs:
            out_path_aux = os.path.join(output_folder_path, voc, '{0}_{1}.nc'.format(voc, date_compact))
            if args.overwrite or not (os.path.isfile(out_path_aux) and os.path.getsize(out_path_aux) > 0):
                pending_vocs.append((voc, out_path_aux))

        if not pending_vocs:
            continue

        print('Date {} out of {}: {} ({} VOCs)'.format(i, daily_dates.size, date.values, len(pending_vocs)))
        time_slice_ds = speciated_vocs_ds.isel(time=i).load()  # buffer entire time frame to speed up things
        for voc, out_path_aux in pending_vocs:
            data = time_slice_ds.sel(voc=voc)

            emission = {
                'name': voc,
                'units': 'kg.m-2.s-1',
                'data': data.data.reshape((1, data.shape[-2], data.shape[-1]))
            }

            print('{}: {}'.format(voc, out_path_aux))

            os.makedirs(os.path.dirname(out_path_aux), exist_ok=True)

            write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [emission], date=pd.to_datetime(date.values),
                         boundary_latitudes=create_bounds(c_lats['data']), boundary_longitudes=create_bounds(c_lons['data']), global_attributes=global_attributes, )

print('DONE')

