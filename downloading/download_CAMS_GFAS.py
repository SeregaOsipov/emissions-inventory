#!/usr/bin/env python
"""Download daily CAMS-GFAS wildfire emissions GRIB files from Copernicus ADS."""

import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
import time
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


def _find_eccodes_tool(name):
    found = shutil.which(name)
    if found:
        return found
    candidate = os.path.join(os.path.dirname(sys.executable), name)
    return candidate if os.path.isfile(candidate) and os.access(candidate, os.X_OK) else None


def ensure_unique_grib_params(grib_file):
    """Strip duplicate paramId records served by ADS before finalizing a GRIB file."""
    grib_ls = _find_eccodes_tool('grib_ls')
    grib_copy = _find_eccodes_tool('grib_copy')
    if not grib_ls or not grib_copy:
        return

    out = subprocess.check_output([grib_ls, '-p', 'count:i,paramId:i', grib_file], text=True)
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((parts[0], parts[1]))

    seen = set()
    kept_counts = []
    for count_str, param_id in rows:
        if param_id not in seen:
            seen.add(param_id)
            kept_counts.append(count_str)

    if len(kept_counts) == len(rows):
        return

    print(
        f'Deduplicating {grib_file} ({len(rows)} -> {len(kept_counts)} unique paramIds)',
        flush=True,
    )
    tmp_grib = f'{grib_file}.dedup.part'
    try:
        subprocess.run(
            [grib_copy, '-w', f"count={'/'.join(kept_counts)}", grib_file, tmp_grib],
            check=True,
        )
        os.replace(tmp_grib, grib_file)
    finally:
        if os.path.exists(tmp_grib):
            os.remove(tmp_grib)


def _retrieve_with_retries(request, out_path, max_attempts=3):
    """Retrieve an ADS request into out_path with exponential backoff."""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            client = cdsapi.Client()
            client.retrieve('cams-global-fire-emissions-gfas', request, out_path)
            return
        except Exception as exc:
            last_exc = exc
            if os.path.exists(out_path):
                os.remove(out_path)
            if attempt < max_attempts:
                wait_s = 15 * (2 ** (attempt - 1))
                print(f'Retry {attempt}/{max_attempts - 1} in {wait_s}s after ADS error: {exc}', flush=True)
                time.sleep(wait_s)
    raise last_exc


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
    try:
        _retrieve_with_retries(request, tmp_target)
        ensure_unique_grib_params(tmp_target)
        os.replace(tmp_target, target)
    finally:
        if os.path.exists(tmp_target):
            os.remove(tmp_target)
    print(f'Completed {target} ({os.path.getsize(target)} bytes)', flush=True)
    return target


def download_chunk(chunk_dates, output_dir):
    """Download a contiguous chunk of dates and split into daily ga_YYYYMMDD.grb files."""
    if len(chunk_dates) == 1:
        return [download_day(chunk_dates[0], output_dir)]

    grib_copy = _find_eccodes_tool('grib_copy')
    if not grib_copy:
        return [download_day(d, output_dir) for d in chunk_dates]

    d_first = chunk_dates[0].strftime('%Y-%m-%d')
    d_last = chunk_dates[-1].strftime('%Y-%m-%d')
    c_first = chunk_dates[0].strftime('%Y%m%d')
    c_last = chunk_dates[-1].strftime('%Y%m%d')

    chunk_part = os.path.join(output_dir, f'.chunk_{c_first}_{c_last}.grb.part')
    split_dir = os.path.join(output_dir, f'.tmp_split_{c_first}_{c_last}')
    request = {
        'variable': GFAS_VARIABLES,
        'date': f'{d_first}/{d_last}',
        'format': 'grib',
    }
    print(f'Downloading chunk {d_first}..{d_last} ({len(chunk_dates)} days)', flush=True)
    outputs = []
    try:
        os.makedirs(split_dir, exist_ok=True)
        _retrieve_with_retries(request, chunk_part)
        subprocess.run(
            [grib_copy, '-f', chunk_part, os.path.join(split_dir, 'ga_[dataDate].grb')],
            check=True,
        )
        for d in chunk_dates:
            dc = d.strftime('%Y%m%d')
            target = os.path.join(output_dir, f'ga_{dc}.grb')
            split_file = os.path.join(split_dir, f'ga_{dc}.grb')
            if not os.path.isfile(split_file) or os.path.getsize(split_file) == 0:
                raise RuntimeError(f'Missing split GRIB for {dc} from chunk {d_first}..{d_last}')
            if os.path.exists(target) and os.path.getsize(target) > 0:
                outputs.append(target)
                continue
            ensure_unique_grib_params(split_file)
            os.replace(split_file, target)
            outputs.append(target)
        print(f'Completed chunk {d_first}..{d_last} ({len(outputs)} daily files)', flush=True)
        return outputs
    finally:
        if os.path.exists(chunk_part):
            os.remove(chunk_part)
        if os.path.isdir(split_dir):
            shutil.rmtree(split_dir, ignore_errors=True)


def build_missing_chunks(dates, output_dir, chunk_days):
    """Group missing dates into contiguous runs capped at chunk_days."""
    missing = [
        d for d in dates
        if not (os.path.exists(os.path.join(output_dir, f"ga_{d.strftime('%Y%m%d')}.grb"))
                and os.path.getsize(os.path.join(output_dir, f"ga_{d.strftime('%Y%m%d')}.grb")) > 0)
    ]
    if not missing:
        return []

    runs = []
    current = [missing[0]]
    for d in missing[1:]:
        if (d - current[-1]).days == 1 and len(current) < chunk_days:
            current.append(d)
        else:
            runs.append(current)
            current = [d]
    runs.append(current)
    return runs


def main():
    parser = argparse.ArgumentParser(description='Download daily CAMS-GFAS GRIB files from Copernicus ADS.')
    parser.add_argument('--mode', '--port', help='Compatibility placeholder for PyCharm debugging.')
    parser.add_argument('--start_date', default='2023-05-15', help='Start date YYYY-MM-DD (inclusive).')
    parser.add_argument('--end_date', default='2023-06-30', help='End date YYYY-MM-DD (inclusive).')
    parser.add_argument('--output_dir', default=_default_output_dir(), help='Directory to write ga_YYYYMMDD.grb files.')
    parser.add_argument('--workers', type=int, default=4, help='Parallel ADS download threads.')
    parser.add_argument('--chunk_days', type=int, default=4, help='Days packed per multi-day ADS request (1 disables packing).')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    dates = [d.to_timestamp() for d in pd.period_range(start=args.start_date, end=args.end_date, freq='D')]
    chunks = build_missing_chunks(dates, args.output_dir, max(1, args.chunk_days))
    skipped = len(dates) - sum(len(c) for c in chunks)
    print(
        f'CAMS-GFAS {args.start_date}..{args.end_date}: {len(dates)} days total, '
        f'{skipped} existing skipped, {len(chunks)} ADS request chunk(s) with {args.workers} workers',
        flush=True,
    )

    if not chunks:
        print('DONE', flush=True)
        return

    failed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_chunk, chunk, args.output_dir): chunk for chunk in chunks}
        for future in concurrent.futures.as_completed(futures):
            chunk = futures[future]
            label = f"{chunk[0].strftime('%Y-%m-%d')}..{chunk[-1].strftime('%Y-%m-%d')}"
            try:
                future.result()
            except Exception as exc:
                print(f'FAILED {label}: {exc}', flush=True)
                failed.append((label, exc))

    if failed:
        raise RuntimeError(f'{len(failed)} chunk(s) failed to download: {[lbl for lbl, _ in failed]}')
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
