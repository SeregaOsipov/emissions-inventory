#!/usr/bin/env python
"""Download targeted EDGAR NetCDF flux archives (*_flx_nc.zip) from JRC OpenData."""

import argparse
import concurrent.futures
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from preproc.preproc_utils import (
    EDGAR_AP_IPCC_SECTORS,
    EDGAR_EIGHT_SECTORS,
    EDGAR_GHG_IPCC_SECTORS,
)

BASE_URL = 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets'

STREAM_SPECS = {
    'EDGAR_2024_GHG': {
        'default_year': 2023,
        'remote_dirs': ['EDGAR_2024_GHG'],
        'pollutants': ['CO2', 'CH4'],
        'sectors': EDGAR_GHG_IPCC_SECTORS,
        'sector_prefix': '',
        'file_prefixes': ['EDGAR_2024_GHG'],
        'local_prefix': 'EDGAR_2024_GHG',
    },
    'v81_FT2022_AP': {
        'default_year': 2022,
        'remote_dirs': ['v81_FT2022_AP_new', 'v81_FT2022_AP'],
        'pollutants': ['BC', 'CO', 'NH3', 'NOx', 'OC', 'PM10', 'PM2.5', 'SO2', 'NMVOC'],
        'sectors': EDGAR_AP_IPCC_SECTORS,
        'sector_prefix': '',
        'file_prefixes': ['v8.1_FT2022_AP'],
        'local_prefix': 'v8.1_FT2022_AP',
    },
    'v81_FT2022_VOC_spec': {
        'default_year': 2022,
        'remote_dirs': ['v81_FT2022_VOC_spec'],
        'pollutants': [f'voc{i}' for i in range(1, 26)],
        'sectors': EDGAR_EIGHT_SECTORS,
        'sector_prefix': 'bkl_',
        'file_prefixes': ['v8.1_FT2022_VOC_spec', 'v81_FT2022_VOC_spec'],
        'local_prefix': 'v8.1_FT2022_VOC_spec',
    },
}


def _default_base_dir():
    return os.environ.get('EDGAR_BASE_DIR', '/HDD1/Data/emissions/EDGAR')


def build_targets(stream, years, base_dir):
    """Build (candidate_urls, local_zip_path) pairs for one EDGAR stream."""
    spec = STREAM_SPECS[stream]
    year_list = years if years else [spec['default_year']]
    targets = []
    for year in year_list:
        for pollutant in spec['pollutants']:
            for sector in spec['sectors']:
                sector_dir = f"{spec['sector_prefix']}{sector}"
                local_name = f"{spec['local_prefix']}_{pollutant}_{year}_{sector_dir}_flx_nc.zip"
                local_path = os.path.join(base_dir, stream, pollutant, sector_dir, 'flx_nc', local_name)
                urls = []
                for remote_dir in spec['remote_dirs']:
                    for file_prefix in spec['file_prefixes']:
                        remote_name = f'{file_prefix}_{pollutant}_{year}_{sector_dir}_flx_nc.zip'
                        urls.append(f'{BASE_URL}/{remote_dir}/{pollutant}/{sector_dir}/flx_nc/{remote_name}')
                targets.append((urls, local_path))
    return targets


def download_one(urls, local_path, timeout):
    """Download the first matching candidate URL to local_path atomically."""
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return 'exists', local_path

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    tmp_path = f'{local_path}.part'
    last_error = None

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'emissions-inventory/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                with open(tmp_path, 'wb') as fh:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        fh.write(chunk)
            if os.path.getsize(tmp_path) == 0:
                os.remove(tmp_path)
                last_error = RuntimeError(f'Empty response from {url}')
                continue
            os.replace(tmp_path, local_path)
            return 'downloaded', local_path
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                last_error = exc
                continue
            last_error = exc
            break
        except Exception as exc:
            last_error = exc
            break
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    if isinstance(last_error, urllib.error.HTTPError) and last_error.code == 404:
        return 'not_found', urls[0]
    return 'error', f'{urls[0]} -> {last_error}'


def parse_args():
    parser = argparse.ArgumentParser(
        description='Download targeted EDGAR *_flx_nc.zip NetCDF flux files from JRC OpenData.'
    )
    parser.add_argument(
        '--streams',
        nargs='+',
        choices=sorted(STREAM_SPECS.keys()),
        default=['EDGAR_2024_GHG', 'v81_FT2022_AP', 'v81_FT2022_VOC_spec'],
        help='EDGAR dataset streams to download.',
    )
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        default=None,
        help='Override reference years for all selected streams (default: 2023 for GHG, 2022 for AP/VOC).',
    )
    parser.add_argument(
        '--base_dir',
        default=_default_base_dir(),
        help='Target EDGAR base directory (default: /HDD1/Data/emissions/EDGAR).',
    )
    parser.add_argument('--timeout', type=int, default=60, help='HTTP request timeout in seconds.')
    parser.add_argument('--workers', type=int, default=4, help='Concurrent HTTP download workers.')
    parser.add_argument('--dry_run', action='store_true', help='Print target count and sample URLs without downloading.')
    return parser.parse_args()


def main():
    args = parse_args()
    all_targets = []
    for stream in args.streams:
        all_targets.extend(build_targets(stream, args.years, args.base_dir))

    print(f'Prepared {len(all_targets)} candidate EDGAR archives for streams={args.streams}', flush=True)
    if args.dry_run:
        for urls, local_path in all_targets[:10]:
            print(f'  {urls[0]} -> {local_path}')
        if len(all_targets) > 10:
            print(f'  ... ({len(all_targets) - 10} more)')
        return

    counts = {'exists': 0, 'downloaded': 0, 'not_found': 0, 'error': 0}
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_one, urls, local_path, args.timeout): (urls, local_path)
            for urls, local_path in all_targets
        }
        for future in concurrent.futures.as_completed(futures):
            status, detail = future.result()
            counts[status] += 1
            if status == 'downloaded':
                print(f'OK: {detail}', flush=True)
            elif status == 'error':
                errors.append(detail)
                if len(errors) <= 10:
                    print(f'ERROR: {detail}', flush=True)

    print(f'Summary: {counts}', flush=True)
    if errors:
        raise RuntimeError(f'{len(errors)} EDGAR archive(s) failed to download (first error: {errors[0]})')


if __name__ == '__main__':
    main()
