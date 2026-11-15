import xarray as xr

xr.set_options(keep_attrs=True)  # IMPORTANT: preserve netcdf attributes during summation

'''
Merge EI pieces together: shipping + rest
'''

fp_root = '/work/mm0062/b302074/Data/AirQuality/EMME/emissions/version_by_country/'
#%% 2017 (original files)
ds1 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20170101_EMME_EDGARv61_HTAPv3_voc_NO_ship_OMI_so2.nc')
ds2 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20170101_EMME_CAMS_ship.nc')
ds = ds1.set_coords(('Times',))+ ds2.set_coords(('Times',))

if 'E_PM_10' not in ds.data_vars:
    ds['E_PM_10'] = ds1.E_PM_10  # shipping EI does not have E_PM10
ds.attrs = ds1.attrs  # preserve global attributes

ds.reset_coords().to_netcdf(fp_root+'HERMESv3_radm2_madesorgam_20170101_EMME.nc')
#%% EDGAR
ds1 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_EDGARv61_HTAPv3_voc_NO_ship_OMI_so2_scenario_HLT.nc')
ds2 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_CAMS_ship_scenario_HLT.nc')
ds = ds1.set_coords(('Times',))+ ds2.set_coords(('Times',))

if 'E_PM_10' not in ds.data_vars:
    ds['E_PM_10'] = ds1.E_PM_10  # shipping EI does not have E_PM10
ds.attrs = ds1.attrs  # preserve global attributes

ds.reset_coords().to_netcdf(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_HLT.nc')
#%% CLE
ds1 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_EDGARv61_HTAPv3_voc_NO_ship_OMI_so2_scenario_CLE.nc')
ds2 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_CAMS_ship_scenario_CLE.nc')
ds = ds1.set_coords(('Times',))+ ds2.set_coords(('Times',))

if 'E_PM_10' not in ds.data_vars:
    ds['E_PM_10'] = ds1.E_PM_10  # shipping EI does not have E_PM10
ds.attrs = ds1.attrs  # preserve global attributes

ds.reset_coords().to_netcdf(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_CLE.nc')
#%% MFR
ds1 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_EDGARv61_HTAPv3_voc_NO_ship_OMI_so2_scenario_MFR.nc')
ds2 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_CAMS_ship_scenario_MFR.nc')
ds = ds1.set_coords(('Times',))+ ds2.set_coords(('Times',))

if 'E_PM_10' not in ds.data_vars:
    ds['E_PM_10'] = ds1.E_PM_10  # shipping EI does not have E_PM10
ds.attrs = ds1.attrs  # preserve global attributes

ds.reset_coords().to_netcdf(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_MFR.nc')
#%% MFR_LV. Assume that shipping emissions are zero. Just link the single file
# fp_root = '/work/mm0062/b302074/Data/AirQuality/EMME/emissions/version_by_country/'
# ds1 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_EDGARv61_HTAPv3_voc_NO_ship_OMI_so2_scenario_HLT.nc')
# ds2 = xr.open_dataset(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_CAMS_ship_scenario_HLT.nc')
# ds = ds1+ds2
# ds.to_netcdf(fp_root+'HERMESv3_radm2_madesorgam_20500101_EMME_HLT.nc')
#%% set the time to 2017
import pandas as pd
import datetime as dt
from climpy.utils.wrf_utils import create_times_var
import netCDF4
import shutil

scenarios = ['HLT', 'CLE', 'MFR', 'MFR_LV']
fp_template = fp_root+'HERMESv3_radm2_madesorgam_{}0101_EMME_{}.nc'

for scenario in scenarios:
    print('processing {}'.format(scenario))
    fp_2017 = fp_template.format(2017, scenario)
    fp_2050 = fp_template.format(2050, scenario)
    shutil.copyfile(fp_2050, fp_2017)  # copy 2050 as 2017 and update time data

    fp = fp_2017
    nc = netCDF4.Dataset(fp, mode='r+')
    dates = pd.date_range(dt.datetime(2017, 1, 1), dt.datetime(2017, 1, 1) + dt.timedelta(days=1*nc['Times'].shape[0]-1), freq='D')
    aux_times = create_times_var(dates)
    nc['Times'][:] = aux_times
    nc.START_DATE = '2017-01-01_00:00:00'  # fix global attribute too
    nc.close()