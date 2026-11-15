import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Geod

'''
This script prepares the TROPOMI NOx emissions for HERMES tool
HERMES input requires "kg.m-2.s-1"
'''

fp_root = '/Users/osipovs/Data/emissions/NOx/NOx_by_Anthony/Gulf_NOx_emissions/'
file_name_template = 'results_Gulf_20220101_to_20230101_EMISSIONS'
#%%


def prep_tropomi_nox_emissions(pp=True):
    '''
    Please find attached the file with gridded emissions for 2019, 2020, 2021, 2022 and 2019-2022, as well as the 0.0625°x0.0625°grid (lon and lat).
    The NOx emissions are in 1e15 molecules/cm2/h.
    They correspond to emissions at 13:00 local time, so if you want to have a daily average you might need to modulate with a daily profile.
    '''

    fp = fp_root + file_name_template + '.csv'
    e_nox_df = pd.read_csv(fp, header=None)

    units_str = '1e15 molecules/cm2/h'
    if pp:
        avogadro_number = 6.022 * 10**23  # Avogadro's number
        e_nox_df = e_nox_df * 10**15 / avogadro_number * 10**10  # moles / km^2 / h
        units_str = 'moles / km^2 / h'

    fp = fp_root + 'results_Gulf_LATITUDE.csv'
    lat_df = pd.read_csv(fp, header=None)

    fp = fp_root + 'results_Gulf_LONGITUDE.csv'
    lon_df = pd.read_csv(fp, header=None)

    da = xr.DataArray(
        data=e_nox_df.to_numpy(),
        dims=['lat_dim', 'lon_dim'],
        coords=dict(
            lon=(["lon_dim"], lon_df.iloc[0,:].to_numpy()),
            lat=(["lat_dim"], lat_df.iloc[:,0].to_numpy()),
        ),
        attrs=dict(
            description="tropomi NOx emissions",
            units=units_str,
        )
    ).sortby('lat').rename({'lat_dim':'lat', 'lon_dim':'lon'})

    # scale the 13:30 emissions (TROPOMI overpass) to yearly average. See table S2 in https://egusphere.copernicus.org/preprints/2023/egusphere-2023-1024/egusphere-2023-1024-supplement.pdf
    power_ratios_montly = [0.967, 0.976, 0.965, 0.932, 0.914, 0.911, 0.918, 0.922, 0.921, 0.924, 0.944, 0.960]  # Ratio between mean daily power demand and power demand at 13:30
    power_ratio_annual = np.array(power_ratios_montly).mean()
    print('Applying power ratio to convert from 13:30 to annual NOx emissions: {}'.format(power_ratio_annual))

    da *= power_ratio_annual

    return da


def get_stag_coordinate_from_regular_rho_grid(coord, drop_last_grid_element=True):
    '''
    Compute staggered grid from regular rho. Drop last
    '''
    dcoord = coord[1:] - coord[:-1]
    dcoord = dcoord[0]
    coord_stag = np.unique([coord - dcoord, coord + dcoord])
    if drop_last_grid_element:
        coord_stag = coord_stag[:-1]

    return coord_stag


def inject_tropomi_grid_info(e_nox_tropomi_ds):
    lon_stag = get_stag_coordinate_from_regular_rho_grid(e_nox_tropomi_ds.lon)
    lat_stag = get_stag_coordinate_from_regular_rho_grid(e_nox_tropomi_ds.lat)

    g = Geod(ellps='WGS84')
    lon2D, lat2D = np.meshgrid(lon_stag, lat_stag)
    _, _, distEW = g.inv(lon2D[:, :-1], lat2D[:, 1:], lon2D[:, 1:], lat2D[:, 1:])
    _, _, distNS = g.inv(lon2D[1:, :], lat2D[1:, :], lon2D[1:, :], lat2D[:-1, :])
    tropomi_grid_area = distEW[1:, :] * distNS[:, 1:]  # m^2

    da = xr.DataArray(
        data=tropomi_grid_area,
        dims=['lat_dim', 'lon_dim'],
        coords=dict(
            lon=(["lon_dim"], e_nox_tropomi_ds.lon.data),
            lat=(["lat_dim"], e_nox_tropomi_ds.lat.data),
        )
    ).sortby('lat').rename({'lat_dim':'lat', 'lon_dim':'lon'})

    e_nox_tropomi_ds['cell_area'] = da  # m^2
    e_nox_tropomi_ds['cell_area'].attrs['units'] = "m2"
    e_nox_tropomi_ds['cell_area'].attrs['long_name'] = "area of the grid cell"
    e_nox_tropomi_ds['cell_area'].attrs['standard_name'] = "area"

    da = xr.DataArray(
        data=np.array([lat_stag[:-1], lat_stag[1:]]).transpose(),
        dims=['lat', 'nv'],
    )
    e_nox_tropomi_ds['lat_bnds'] = da

    da = xr.DataArray(
        data=np.array([lon_stag[:-1], lon_stag[1:]]).transpose(),
        dims=['lon', 'nv'],
    )
    e_nox_tropomi_ds['lon_bnds'] = da


if __name__ == '__main__':
    #%%
    da = prep_tropomi_nox_emissions()
    e_nox_tropomi_ds = da.to_dataset(name='nox_no2')
    inject_tropomi_grid_info(e_nox_tropomi_ds)

    nox_mm = 14+16*2  # g/mol  # 14 + x16  # Double check with Anthony is it NO or NO2 as it affects the total mass
    e_nox_tropomi_ds['nox_no2'] *= nox_mm * 10 ** -3 * 10**-6 / 3600  # 'moles / km^2 / h' ->  "kg.m-2.s-1"
    e_nox_tropomi_ds['nox_no2'].attrs['units'] = 'kg.m-2.s-1'
    #%% write the file
    output_fp = fp_root + file_name_template + '_raw.nc'
    e_nox_tropomi_ds.to_netcdf(output_fp)
    print('Saved Raw file {}'.format(output_fp))

    # remove negative values
    print('min is {}'.format(e_nox_tropomi_ds['nox_no2'].min()))
    e_nox_tropomi_ds['nox_no2'] = e_nox_tropomi_ds.nox_no2.where(e_nox_tropomi_ds.nox_no2 > 0).fillna(0)
    print('new min is {}'.format(e_nox_tropomi_ds['nox_no2'].min()))

    # e_nox_tropomi_ds['lon_bnds'] = e_nox_tropomi_ds['lon']
    # e_nox_tropomi_ds['lat_bnds'] = e_nox_tropomi_ds['lat']

    # have to make the file CF complaint for ESMF regridding
    e_nox_tropomi_ds['lat'].attrs['bounds'] = "lat_bnds"
    e_nox_tropomi_ds['lat'].attrs['units'] = "degrees_north"
    e_nox_tropomi_ds['lat'].attrs['axis'] = "Y"
    e_nox_tropomi_ds['lat'].attrs['long_name'] = "latitude"
    e_nox_tropomi_ds['lat'].attrs['standard_name'] = "latitude"

    e_nox_tropomi_ds['lon'].attrs['bounds'] = "lon_bnds"
    e_nox_tropomi_ds['lon'].attrs['units'] = "degrees_east"
    e_nox_tropomi_ds['lon'].attrs['axis'] = "X"
    e_nox_tropomi_ds['lon'].attrs['long_name'] = "longitude"
    e_nox_tropomi_ds['lon'].attrs['standard_name'] = "longitude"

    output_fp = fp_root + file_name_template + '.nc'
    e_nox_tropomi_ds.to_netcdf(output_fp)

    print('Saved PP-ed file {}'.format(output_fp))