import geopandas as gpd
from fiona.drvsupport import supported_drivers
supported_drivers['LIBKML'] = 'rw'
import regionmask
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

'''
This script spatially merges two datasets using custom polygon over larger Arabian Gulf region 
'''
#%%
fp_root = '/work/mm0062/b302074/Data/AirQuality/THOFA/emissions/'
fp_edgar = fp_root + 'HERMESv3_radm2_madesorgam_20230515_THOFA.nc'
fp_tropomi = fp_root + 'HERMESv3_radm2_madesorgam_20230515_THOFA_TROPOMI_NOx.nc'
output_fp_hybrid = fp_root + 'HERMESv3_radm2_madesorgam_20230515_THOFA_EDGAR_TROPOMI_hybrid.nc'
#%% prep WRF grid
wrf_grid_fp = fp_root + '../chem_100_v2/output/wrfout_d01_2023-05-15_00_00_00'
grid_ds = xr.open_dataset(wrf_grid_fp)[['XLONG', 'XLAT']].isel(Time=0)  # have to get coordinates somewhere
#%% Apply the custom-made mask. Redo the Mask using Google Earth
fp = fp_root + 'TROPOMI_GCC.kml'
gdf = gpd.read_file(fp, driver='LIBKML')  # LIBKML
#%%
ds_edgar = xr.open_dataset(fp_edgar)
ds_tropomi = xr.open_dataset(fp_tropomi)
#%%
# mask = regionmask.mask_3D_geopandas(gdf, ds_edgar.lon, ds_edgar.lat)  # hermes does not store coordinates
mask = regionmask.mask_3D_geopandas(gdf, grid_ds.XLONG, grid_ds.XLAT)
reg_mask = mask.sel(region=0)

hybrid_nox_da = ds_edgar.E_NO.where(np.logical_not(reg_mask), ds_tropomi.E_NO)  # choose where to KEEP data and provide a substitue otherwise
ds_edgar['E_NO'] = hybrid_nox_da
ds_edgar.drop_vars(['XLONG', 'XLAT', 'XTIME', 'region']).to_netcdf(output_fp_hybrid)  # original HERMES output does not store this variables

#%% Boost VOCs
'''
https://www.nature.com/articles/s41467-020-14375-0
The ethane, propane, n-butanes, and i-butane emissions were scaled by factors of 1.9, 1.7, 1.0, and 0.43, respectively, to match recent global emission estimates in the literature
'''
fp_in = output_fp_hybrid
fp_out = fp_root + 'HERMESv3_radm2_madesorgam_20230515_THOFA_EDGAR_TROPOMI_hybrid_VOCs_boost.nc'

in_ds = xr.open_dataset(fp_in)
in_ds['E_ETH'] *= 1.9
in_ds['E_HC3'] *= 1.7

in_ds.to_netcdf(fp_out)

#%% Boost VOC emissions over the Turkey
fp_in = fp_root + 'HERMESv3_radm2_madesorgam_HTAPv3_20230515_THOFA.nc'
fp_out = fp_root + 'HERMESv3_radm2_madesorgam_HTAPv3_20230515_THOFA_VOCs_boost_Turkey_boost.nc'

in_ds = xr.open_dataset(fp_in)
in_boosted_ds = xr.open_dataset(fp_in)

for key in 'E_HC3,E_HC5,E_HC8,E_ETH'.split(','):
    in_boosted_ds[key] *= 10  # boost emissions by 10

regionmask_countries = regionmask.defined_regions.natural_earth_v5_0_0.countries_50
mask = regionmask_countries.mask_da(grid_ds.XLONG, grid_ds.XLAT)
mask_Turkey = mask.cf == "TR"
in_ds_boosted_Turkey = in_boosted_ds.where(mask_Turkey,in_ds)

# fix the dataset to be again WRF complaint
out_ds = in_ds_boosted_Turkey.drop_vars(['XLONG', 'XLAT', 'XTIME'])
out_ds['Times'] = in_ds['Times']
out_ds.to_netcdf(fp_out)



