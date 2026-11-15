#!/usr/bin/env python
"""Download daily CAMS-GFAS wildfire emissions GRIB files from Copernicus ADS."""

import argparse
import concurrent.futures
import os
import cdsapi
import pandas as pd


GFAS_VARIABLES = [
    'altitude_of_plume_top',
    'mean_altitude_of_maximum_injection',
    'wildfire_combustion_rate',
    'wildfire_flux_of_acetaldehyde',
    'wildfire_flux_of_acetone',
    'wildfire_flux_of_ammonia',
    'wildfire_flux_of_benzene',
    'wildfire_flux_of_black_carbon',
    'wildfire_flux_of_butanes',
    'wildfire_flux_of_butenes',
    'wildfire_flux_of_carbon_dioxide',
    'wildfire_flux_of_carbon_monoxide',
    'wildfire_flux_of_dimethyl_sulfide',
    'wildfire_flux_of_ethane',
    'wildfire_flux_of_ethanol',
    'wildfire_flux_of_ethene',
    'wildfire_flux_of_formaldehyde',
    'wildfire_flux_of_heptane',
    'wildfire_flux_of_hexanes',
    'wildfire_flux_of_hexene',
    'wildfire_flux_of_higher_alkanes',
    'wildfire_flux_of_higher_alkenes',
    'wildfire_flux_of_hydrogen',
    'wildfire_flux_of_isoprene',
    'wildfire_flux_of_methane',
    'wildfire_flux_of_methanol',
    'wildfire_flux_of_nitrogen_oxides',
    'wildfire_flux_of_nitrous_oxide',
    'wildfire_flux_of_non_methane_hydrocarbons',
    'wildfire_flux_of_octene',
    'wildfire_flux_of_organic_carbon',
    'wildfire_flux_of_particulate_matter_d_2_5_µm',
    'wildfire_flux_of_pentanes',
    'wildfire_flux_of_pentenes',
    'wildfire_flux_of_propane',
    'wildfire_flux_of_propene',
    'wildfire_flux_of_sulphur_dioxide',
    'wildfire_flux_of_terpenes',
    'wildfire_flux_of_toluene',
    'wildfire_flux_of_toluene_lump',
    'wildfire_flux_of_total_carbon_in_aerosols',
    'wildfire_flux_of_total_particulate_matter',
    'wildfire_flux_of_xylene',
    'wildfire_fraction_of_area_observed',
    'wildfire_overall_flux_of_burnt_carbon',
    'wildfire_radiative_power',
]


def _default_output_dir():
    data_root = os.environ.get('EMISSIONS_DATA_ROOT', '/HDD1/Data/emissions')
    return os.path.join(data_root, 'CAMS-GFAS')


def download_day(date, output_dir):
    """Download one daily CAMS-GFAS GRIB file if missing or empty."""
    date_iso = date.strftime('%Y-%m-%d')
    date_compact = date.strftime('%Y%m%d')
    target = os.path.join(output_dir, f'ga_{date_compact}.grb')

    if os.path.exists(target) and os.path.getsize(target) > 0:
        print(f'Skipping existing {target} ({os.path.getsize(target)} bytes)', flush=True)
        return target

    tmp_target = f'{target}.part'
    request = {
        'variable': GFAS_VARIABLES,
        'date': f'{date_iso}/{date_iso}',
        'format': 'grib',
    }
    print(f'Downloading {date_iso} -> {target}', flush=True)
    client = cdsapi.Client()
    client.retrieve('cams-global-fire-emissions-gfas', request, tmp_target)
    os.replace(tmp_target, target)
    print(f'Completed {target} ({os.path.getsize(target)} bytes)', flush=True)
    return target


def main():
    parser = argparse.ArgumentParser(description='Download daily CAMS-GFAS GRIB files from Copernicus ADS.')
    parser.add_argument('--mode', '--port', help='Compatibility placeholder for PyCharm debugging.')
    parser.add_argument('--start_date', default='2023-05-15', help='Start date YYYY-MM-DD (inclusive).')
    parser.add_argument('--end_date', default='2023-06-30', help='End date YYYY-MM-DD (inclusive).')
    parser.add_argument('--output_dir', default=_default_output_dir(), help='Directory to write ga_YYYYMMDD.grb files.')
    parser.add_argument('--workers', type=int, default=4, help='Parallel ADS download threads.')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    dates = [d.to_timestamp() for d in pd.period_range(start=args.start_date, end=args.end_date, freq='D')]
    print(f'Downloading {len(dates)} daily CAMS-GFAS files ({args.start_date} to {args.end_date}) into {args.output_dir} with {args.workers} workers', flush=True)

    failed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_day, d, args.output_dir): d for d in dates}
        for future in concurrent.futures.as_completed(futures):
            d = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f'FAILED {d.strftime("%Y-%m-%d")}: {exc}', flush=True)
                failed.append((d, exc))

    if failed:
        raise RuntimeError(f'{len(failed)} day(s) failed to download: {[d.strftime("%Y-%m-%d") for d, _ in failed]}')
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
