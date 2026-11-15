#!/usr/bin/env python

#%load_ext autoreload
#%autoreload 2

import argparse
import os
import xarray as xr
import numpy as np
from warnings import warn as warning

from hermesv3_gr.tools.netcdf_tools import get_grid_area
from preproc.preproc_utils import write_netcdf, EDGAR_EIGHT_SECTORS, unzip_edgar_files, EDGAR_AP_IPCC_SECTORS, EDGAR_GHG_IPCC_SECTORS

# ============== README ======================
"""
v8.1
website https://edgar.jrc.ec.europa.eu/dataset_ghg2024
downloading: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/EDGAR_2024_GHG/
I need emissions units to be: "kg m-2 s-1". So take Emission Flux file (_flx.nc)

Run in terminal:
cd /scratch/osipovs/iops/sw/workspace/hermesv3_gr;
source /project/k10066/osipovs/.commonrc; gogomamba; mamba activate py311
python -u preproc/edgar_v81_preproc.py >& log.edgar_v81_ghg_preproc

Issues (TODO):
1. EDGAR reports nox, which not clear no or no2. Hermes treated it as NO2. I did the same.
3. There is an issues that different Air Pollutants have different sectors representation
"""

# ===================
PROCESS_YEARLY = True  # False
PROCESS_MONTHLY = False  # True
LIST_YEARS = [2017, 2021, 2022, 2023]
# ============== GHG ======================
DATA_STREAM='EDGAR_2024_GHG'
LIST_POLLUTANTS = ['CO2', 'CH4', ]  # 'BC', 'CO', 'NH3', 'NOx', 'OC', 'PM10', 'PM2.5', 'SO2', 'NMVOC']
monthly_sectors = EDGAR_EIGHT_SECTORS
yearly_sectors = EDGAR_GHG_IPCC_SECTORS
INPUT_NAME_TEMPLATE = '<pollutant>/<sector>/flx_nc/<stream>_<pollutant>_<year>_<sector>{}'.replace('<stream>', DATA_STREAM)
ARCHIVE_NAME_TEMPLATE = INPUT_NAME_TEMPLATE
# ============== APs ======================
DATA_STREAM='v81_FT2022_AP'
DATA_STREAM_FOR_FILE_NAME='v8.1_FT2022_AP'  # I decided not to rename the files
LIST_POLLUTANTS = ['BC', 'CO', 'NH3', 'NOx', 'OC', 'PM10', 'PM2.5', 'SO2', 'NMVOC']  # TODO: I probably have to implement pollutant-specific list of sectors
monthly_sectors = EDGAR_EIGHT_SECTORS
yearly_sectors = EDGAR_AP_IPCC_SECTORS
INPUT_NAME_TEMPLATE = '<pollutant>/<sector>/flx_nc/<stream>_<pollutant>_<year>_<sector>{}'.replace('<stream>', DATA_STREAM_FOR_FILE_NAME)
ARCHIVE_NAME_TEMPLATE = INPUT_NAME_TEMPLATE
# ============== VOC ======================
'''
Conventions:
1. variable names can not have dots in it, because it will be evaluated (as a valid python expression) in speciation profile (e.g., 15*pm25)
Issues:
1. The naming of the dataset is inconsistent. Sometimes it is v8.1 and sometimes it is v81. The unziped files are renamed to v81.
2. 2022 was missing voc11 in FUEL EXPLOITATION sector and was ignored
3. sector WASTE does not have voc16, voc20
4. voc25 (Other NMVOC) is not allocated anywhere in speciation profile due to unknown formula. https://edgar.jrc.ec.europa.eu/dataset_ap81_VOC_spec
'''

DATA_STREAM='v81_FT2022_VOC_spec'
LIST_POLLUTANTS = ['voc{}'.format(i) for i in range(1, 26)]
monthly_sectors = None  # EDGAR_MONTHLY_SECTORS  # Does not exist
yearly_sectors = EDGAR_EIGHT_SECTORS
RENAME_INPUT_NAME_TEMPLATE = '<pollutant>/bkl_<sector>/flx_nc/<stream>_<pollutant>_<year>_bkl_<sector>{}'.replace('<stream>', 'v8.1_FT2022_VOC_spec')  # aux template to rename v8.1 to v81
INPUT_NAME_TEMPLATE = '<pollutant>/bkl_<sector>/flx_nc/<stream>_<pollutant>_<year>_bkl_<sector>{}'.replace('<stream>', DATA_STREAM)
ARCHIVE_NAME_TEMPLATE = '<pollutant>/bkl_<sector>/flx_nc/<stream>_<pollutant>_<year>_bkl_<sector>{}'.replace('<stream>', 'v8.1_FT2022_VOC_spec')


# ============== STREAM CONFIGURATIONS ======================
STREAM_CONFIGS = {
    'EDGAR_2024_GHG': {
        'pollutants': ['CO2', 'CH4'],
        'monthly_sectors': EDGAR_EIGHT_SECTORS,
        'yearly_sectors': EDGAR_GHG_IPCC_SECTORS,
        'file_stream': 'EDGAR_2024_GHG',
    },
    'v81_FT2022_AP': {
        'pollutants': ['BC', 'CO', 'NH3', 'NOx', 'OC', 'PM10', 'PM2.5', 'SO2', 'NMVOC'],
        'monthly_sectors': EDGAR_EIGHT_SECTORS,
        'yearly_sectors': EDGAR_AP_IPCC_SECTORS,
        'file_stream': 'v8.1_FT2022_AP',
    },
    'v81_FT2022_VOC_spec': {
        'pollutants': ['voc{}'.format(i) for i in range(1, 26)],
        'monthly_sectors': None,
        'yearly_sectors': EDGAR_EIGHT_SECTORS,
        'file_stream': 'v81_FT2022_VOC_spec',
    },
}

DEFAULT_BASE_DIR = os.environ.get('EDGAR_BASE_DIR', '/HDD1/Data/emissions/EDGAR')
DATA_STREAM = 'EDGAR_2024_GHG'
LIST_POLLUTANTS = STREAM_CONFIGS[DATA_STREAM]['pollutants']
monthly_sectors = STREAM_CONFIGS[DATA_STREAM]['monthly_sectors']
yearly_sectors = STREAM_CONFIGS[DATA_STREAM]['yearly_sectors']
INPUT_PATH = os.path.join(DEFAULT_BASE_DIR, DATA_STREAM)
OUTPUT_PATH = os.path.join(INPUT_PATH, 'hermes_pp')
INPUT_NAME = '<pollutant>/<sector>/flx_nc/{}_<pollutant>_<year>_<sector>_flx.nc'.format(DATA_STREAM)
ARCHIVE_INPUT_NAME = '<pollutant>/<sector>/flx_nc/{}_<pollutant>_<year>_<sector>_flx_nc.zip'.format(DATA_STREAM)
PROCESS_MONTHLY = False
PROCESS_YEARLY = True


def do_monthly_transformation(year, pollutants, sectors, name_template):

    # year=2023
    # sectors=EDGAR_MONTHLY_SECTORS
    # sector=sectors[0]
    # pollutant='CH4'
    # month=1

    for pollutant in pollutants:
        print('Processing pollutant {}'.format(pollutant))
        for sector in sectors:  # ipcc in list(ipcc_to_sector_dict().keys()):
            # sector = ipcc_to_sector_dict()[ipcc]
            print('\t sector {}'.format(sector))
            for month in range(1, 12 + 1, 1):
                file_path = os.path.join(INPUT_PATH,  name_template.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<month>', str(month)).replace('<sector>', sector))

                if os.path.exists(file_path):
                    grid_area = get_grid_area(file_path)
                    print('in: {}'.format(file_path))
                    # nc_in = Dataset(file_path, mode='r')
                    nc_in = xr.open_dataset(file_path)
                    nc_in = nc_in.isel(time=(nc_in.time.dt.month==month))  #  EDGAR stores 12 month in a single file

                    # pollutant = pollutant.replace('.', '')  # PM2.5 case

                    data = np.array(nc_in.fluxes)
                    lats = nc_in.lat
                    lons = nc_in.lon
                    nc_in.close()

                    data_attributes = {'long_name': pollutant.lower(),
                                       'units': 'kg.m-2.s-1',
                                       'coordinates': 'lat lon',
                                       'grid_mapping': 'crs'}

                    out_path_aux = os.path.join(OUTPUT_PATH, 'monthly_mean', pollutant.lower() + '_' + sector.lower())
                    if not os.path.exists(out_path_aux):
                        os.makedirs(out_path_aux)
                    nc_file_path = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(pollutant.lower(), year, str(month).zfill(2)))
                    # print('Writing to {}'.format(nc_file_path))
                    write_netcdf(nc_file_path, data, data_attributes, lats, lons, grid_area, year, sector.lower())
                else:
                    warning("The pollutant {} for the sector {} does not exist.\n File not found: {}".format(pollutant, sector, file_path))
    return True


def do_yearly_transformation(year, pollutants, sectors, name_template):
    # year=2023
    # sectors=EDGAR_MONTHLY_SECTORS
    # sector=sectors[0]
    # pollutant='CH4'
    # month=1

    missing_files = []

    for pollutant in pollutants:
        print('Processing pollutant {}'.format(pollutant))
        for sector in sectors:
            print('\t sector {}'.format(sector))
            file_path = os.path.join(INPUT_PATH,  name_template.replace('<pollutant>', pollutant).replace('<year>', str(year)).replace('<sector>', sector))

            if os.path.exists(file_path):
                grid_area = get_grid_area(file_path)
                print('in: {}'.format(file_path))
                # nc_in = Dataset(file_path, mode='r')
                nc_in = xr.open_dataset(file_path)

                # I can't have dots in the variable name (it will be evaluated in python)
                out_pollutant = pollutant.replace('.', '')  # PM2.5 case
                if pollutant.lower() == 'nox':
                    out_pollutant = 'nox_no2'

                data = np.array(nc_in.fluxes)
                lats = nc_in.lat
                lons = nc_in.lon
                nc_in.close()

                data_attributes = {'long_name': out_pollutant.lower(),
                                   'units': 'kg.m-2.s-1',
                                   'coordinates': 'lat lon',
                                   'grid_mapping': 'crs'}

                out_path_aux = os.path.join(OUTPUT_PATH, 'yearly_mean', out_pollutant.lower() + '_' + sector.lower())
                if not os.path.exists(out_path_aux):
                    os.makedirs(out_path_aux)
                nc_file_path = os.path.join(out_path_aux, '{0}_{1}.nc'.format(out_pollutant.lower(), year))
                write_netcdf(nc_file_path, data, data_attributes, lats, lons, grid_area, year, sector.lower())
            else:
                # TODO: Think how to make this fail-proof
                warning("The pollutant {} for the sector {} does not exist.\n File not found: {}".format(pollutant, sector, file_path))
                missing_files.append(file_path)
                #raise Exception("The pollutant {} for the sector {} does not exist.\n File not found: {}".format(pollutant, sector, file_path))
    print('\nMissing files:\n{}\n'.format('\n'.join(missing_files)))

    return True


def fix_v81_FT2022_VOC_names(year):  # replace v8.1 with v81
    for sector in yearly_sectors:
        for pollutant in LIST_POLLUTANTS:
            temp_input_name = RENAME_INPUT_NAME_TEMPLATE.format('_flx.nc')
            file_path = os.path.join(INPUT_PATH, temp_input_name.replace('<pollutant>', pollutant).replace('<sector>',sector).replace('<year>', str(year)))
            print(file_path)
            if os.path.exists(file_path):
                os.rename(file_path, file_path.replace('v8.1', 'v81'))
                print('Renamed {}'.format(file_path))


def parse_args():
    parser = argparse.ArgumentParser(description='Preprocess EDGAR v8.1 / 2024_GHG / VOC_spec NetCDF fluxes for HERMESv3_GR.')
    parser.add_argument('--stream', choices=sorted(STREAM_CONFIGS.keys()), default='EDGAR_2024_GHG', help='EDGAR dataset stream.')
    parser.add_argument('--years', nargs='+', type=int, default=[2022], help='Years to process (default: 2022).')
    parser.add_argument('--base_dir', default=DEFAULT_BASE_DIR, help='Root EDGAR directory (default: /HDD1/Data/emissions/EDGAR).')
    parser.add_argument('--monthly', action='store_true', help='Run monthly preprocessing instead of yearly.')
    parser.add_argument('--skip_unzip', action='store_true', help='Skip unzipping *_flx_nc.zip archives.')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    cfg = STREAM_CONFIGS[args.stream]
    DATA_STREAM = args.stream
    LIST_YEARS = args.years
    LIST_POLLUTANTS = cfg['pollutants']
    monthly_sectors = cfg['monthly_sectors']
    yearly_sectors = cfg['yearly_sectors']
    PROCESS_MONTHLY = args.monthly
    PROCESS_YEARLY = not args.monthly

    INPUT_PATH = os.path.join(args.base_dir, DATA_STREAM)
    OUTPUT_PATH = os.path.join(INPUT_PATH, 'hermes_pp')

    input_tpl = '<pollutant>/<sector>/flx_nc/<stream>_<pollutant>_<year>_<sector>{}'.replace('<stream>', cfg['file_stream'])
    archive_tpl = '<pollutant>/<sector>/flx_nc/<stream>_<pollutant>_<year>_<sector>{}'.replace(
        '<stream>', 'v8.1_FT2022_VOC_spec' if DATA_STREAM == 'v81_FT2022_VOC_spec' else cfg['file_stream']
    )
    if PROCESS_MONTHLY or DATA_STREAM == 'v81_FT2022_VOC_spec':
        input_tpl = input_tpl.replace('<sector>', 'bkl_<sector>')
        archive_tpl = archive_tpl.replace('<sector>', 'bkl_<sector>')

    INPUT_NAME = input_tpl.format('_flx.nc')
    ARCHIVE_INPUT_NAME = archive_tpl.format('_flx_nc.zip')
    print('INPUT_PATH {}'.format(INPUT_PATH))
    print('INPUT_NAME {}'.format(INPUT_NAME))
    print('ARCHIVE_INPUT_NAME {}'.format(ARCHIVE_INPUT_NAME))

    if PROCESS_MONTHLY:
        if monthly_sectors is None:
            raise ValueError('Stream {} does not support monthly preprocessing'.format(DATA_STREAM))
        print('Process Monthly')
        if not args.skip_unzip:
            unzip_edgar_files(None, LIST_POLLUTANTS, monthly_sectors, INPUT_PATH, 'monthly/' + ARCHIVE_INPUT_NAME)
        for year in LIST_YEARS:
            do_monthly_transformation(year, LIST_POLLUTANTS, monthly_sectors, 'monthly/' + INPUT_NAME)

    if PROCESS_YEARLY:
        print('Process Yearly')
        for year in LIST_YEARS:
            print('Year {}'.format(year))
            if not args.skip_unzip:
                unzip_edgar_files(year, LIST_POLLUTANTS, yearly_sectors, INPUT_PATH, ARCHIVE_INPUT_NAME)
            if DATA_STREAM == 'v81_FT2022_VOC_spec':
                fix_v81_FT2022_VOC_names(year)
            do_yearly_transformation(year, LIST_POLLUTANTS, yearly_sectors, INPUT_NAME)

    print('DONE')
