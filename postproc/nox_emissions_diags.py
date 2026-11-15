import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import regionmask
from scipy.constants import golden

from Papers.THOFA.emissions.pp_tropomi_nox_emissions import prep_tropomi_nox_emissions
from climpy.utils.file_path_utils import get_pictures_root_folder
from climpy.utils.plotting_utils import JGR_page_width_inches, save_figure_bundle
from climpy.utils.pop_utils import middle_eastern_countries_in_AQABA_WRF_domain, middle_eastern_countries_in_AQABA_WRF_domain_for_table
from climpy.utils.wrf_utils import derive_wrf_cells_area
import cartopy.crs as ccrs
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap

pics_output_folder = get_pictures_root_folder() + '/Papers/AirQuality/emissions/'
#%% Prep TROPOMI NOx emissions from Anthony
fp = '/work/mm0062/b302074/Data/emissions/NOx/NOx_by_Anthony/Gulf_NOx_emissions/results_Gulf_20220101_to_20230101_EMISSIONS.nc'
fp = '/Users/osipovs/Data/emissions/NOx/NOx_by_Anthony/Gulf_NOx_emissions/results_Gulf_20220101_to_20230101_EMISSIONS.nc'
e_nox_tropomi_ds = xr.open_dataset(fp)  # kg.m-2.s-1
#%% Prep WRF emissions
fp = '/Users/osipovs/Data/AirQuality/THOFA/HERMESv3_radm2_madesorgam_20230515_THOFA_EDGARv5_HTAP_voc_CAMS_ship_OMI_so2.nc'
e_wrf_ds = xr.open_dataset(fp).mean('Time')  # units = "mol km^-2 hr^-1"

wrf_grid_ds = xr.open_dataset('/Users/osipovs/Data/AirQuality/THOFA/IC_BC/met_em/met_em.d01.2023-06-30_00_00_00.nc')
e_wrf_ds['lon'] = wrf_grid_ds['XLONG_M'][0]
e_wrf_ds['lat'] = wrf_grid_ds['XLAT_M'][0]
e_wrf_ds = e_wrf_ds.set_coords(['lon', 'lat'])

e_wrf_ds['cell_area'] = derive_wrf_cells_area(wrf_grid_ds)  # m^2

wrf_grid_ds = wrf_grid_ds.rename({'south_north':'lat', 'west_east':'lon'})
e_wrf_ds = e_wrf_ds.rename({'south_north':'lat', 'west_east':'lon'})

e_wrf_ds = e_wrf_ds.set_coords('cell_area')
#%% EDGAR v6.1
fp = '/work/mm0062/b302074/Data/emissions/EDGAR/v61_AP/NOx/TOTALS/EDGARv6.1_NOx_2018_TOTALS.0.1x0.1.nc'
e_nox_edgar61_ds = xr.open_dataset((fp))
#%%


def extract_diag_by_country(input_ds, country):  # country in middle_eastern_countries_in_AQABA_WRF_domain:
    regionmask_countries = regionmask.defined_regions.natural_earth_v5_0_0.countries_50
    mask = regionmask_countries.mask_da(input_ds)  # mask all countries even partial overlap

    country_index = regionmask_countries.map_keys(country)
    print('{}:{}'.format(country, country_index))
    in_country_ds = input_ds.where(mask == country_index)
    return in_country_ds


def integrate_diag_across_countries(input_ds):
    dss_by_country = []
    # process countries individually
    for country in middle_eastern_countries_in_AQABA_WRF_domain:
        # print('{}:{}'.format(country, country_index))
        in_country_ds = extract_diag_by_country(input_ds, country)
        dss_by_country += [in_country_ds.sum(), ]

    nox_by_country_ds = xr.concat(dss_by_country, dim='country')
    nox_by_country_ds['country'] = middle_eastern_countries_in_AQABA_WRF_domain_for_table  # middle_eastern_countries_in_AQABA_WRF_domain

    return nox_by_country_ds
#%% prep pped EDGAR
'/work/mm0062/b302074/Data/AirQuality/emissions/hermes/datasets/EDGAR/v5/hermes_pp/monthly_mean/nox_no2_ene'
fp = '/work/mm0062/b302074/Data/AirQuality/emissions/hermes/datasets/EDGAR/v50_AP/NOx/TOTALS/v50_NOx_2015.0.1x0.1.nc'
fp = '/Users/osipovs/Downloads/v50_NOx_2015.0.1x0.1.nc'
edgar_ds = xr.open_dataset(fp)  # "kg m-2 s-1" ;

fp = '/Users/osipovs/Downloads/nox_no2_201506.nc'
edgar_grid_ds = xr.open_dataset(fp, decode_times=False)

e_by_country_edgar = integrate_diag_across_countries(edgar_ds * edgar_grid_ds.cell_area)  # kg / sec
e_by_country_edgar.transpose().to_pandas() * 10**-6 * (365*24*60*60)  # kt / year  # EDGAR
#%% Normalize units across all datasets: convert to "mol km^-2 hr^-1"
nox_mm = 14+16*2  # g/mol  # 14 + x16
e_nox_tropomi_ds['nox_no2'] = e_nox_tropomi_ds.nox_no2 * 10**3 / nox_mm * 10**6 * 3600  # kg m^-2 sec^-1 -> "mol km^-2 hr^-1"
e_nox_tropomi_ds.nox_no2.attrs['units'] = 'mol km^-2 hr^-1'
#%% Compare Totals
e_nox_by_country_tropomi = integrate_diag_across_countries(e_nox_tropomi_ds.nox_no2 * e_nox_tropomi_ds.cell_area * 10**-6)  # moles / hr
e_by_country_wrf = integrate_diag_across_countries(e_wrf_ds * e_wrf_ds['cell_area'] * 10**-6)  # moles / hr
# e_nox_by_country = xr.concat([e_nox_by_country_tropomi, e_by_country_wrf.E_NO], dim='source')
# e_nox_by_country['source'] = ['tropomi', 'wrf']

# factors to convert to # kt / year
# f_tropomi = nox_mm * 10 ** -6 * (60*60*24 * 365)  # kt / year
f_tropomi = nox_mm * 10 ** -9 * (24 * 365)  # kt / year
f_wrf = nox_mm * 10 ** -9 * (24 * 365)  # kt / year
f_edgar = 10**-6 * (365*24*60*60)  # kt / year
e_nox_by_country = xr.concat([e_nox_by_country_tropomi * f_tropomi, e_by_country_wrf.E_NO * f_wrf], dim='source')  # kt / year
e_nox_by_country['source'] = ['tropomi', 'wrf']
# e_nox_by_country = xr.concat([e_nox_by_country_tropomi * f_tropomi, e_by_country_wrf.E_NO * f_wrf, e_by_country_edgar.emi_nox * f_edgar], dim='source')  # kt / year
# e_nox_by_country['source'] = ['tropomi', 'wrf', 'edgar']

e_nox_by_country.transpose().to_pandas()
#%%


def plot_emis_map(da, contourf_levels, ax=None):
    if ax is None:
        # figsize = (JGR_page_width_inches() * 1.5, JGR_page_width_inches() / golden * 1.5)
        figsize = (JGR_page_width_inches() * 3, JGR_page_width_inches() / golden * 3)
        fig = plt.figure(figsize=figsize)
        # projection = ccrs.LambertCylindrical()
        projection = ccrs.PlateCarree()
        ax = fig.add_subplot(1, 1, 1, projection=projection)

    if contourf_levels.min() * contourf_levels.max() < 0:
        norm = TwoSlopeNorm(vmin=contourf_levels.min(), vcenter=0, vmax=contourf_levels.max())
        c_handle = ax.contourf(da['lon'], da['lat'], da, levels=contourf_levels, extend='both', cmap='bwr', norm=norm)
    else:
        palette = ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
        palette = ['white', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']  # drop black as it makes difficult to see coastlines
        cm = LinearSegmentedColormap.from_list('GEE', palette, N=256)
        c_handle = ax.contourf(da['lon'], da['lat'], da, levels=contourf_levels, extend='both', cmap=cm)
        # c_handle = da.plot.contourf(ax=ax, levels=contourf_levels, extend='both', cmap=cm)
    plt.colorbar(c_handle)#, cax=pos_cax)
    ax.coastlines()
    # ax.set_xticks(np.linspace(-180, 180, 5), crs=projection)
    # ax.set_yticks(np.linspace(-90, 90, 5), crs=projection)
    # gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
    #                   linewidth=2, color='gray', alpha=0.5, linestyle='--')
    return ax


#%% Plot Iraq maps
country = 'Iraq'
e_country_tropomi = extract_diag_by_country(e_nox_tropomi_ds, country)  # moles/ km2/hr
e_country_wrf = extract_diag_by_country(e_wrf_ds.E_NO, country).squeeze() # moles/ km2/hr

fig, axes = plt.subplots(nrows=1, ncols=2, subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(20, 10), constrained_layout=True)
contourf_levels = np.linspace(-2.5, 5, 80)
contourf_levels = np.linspace(e_country_tropomi.quantile(0.05), e_country_tropomi.quantile(0.95), 80)
plot_emis_map(e_country_tropomi, contourf_levels, ax=axes[0])
axes[0].set_extent([38.5, 49, 28.5, 37.5])#, crs=ccrs.PlateCarree())
plot_emis_map(e_country_wrf, contourf_levels, ax=axes[1])
axes[1].set_extent([38.5, 49, 28.5, 37.5])#, crs=ccrs.PlateCarree())
plt.suptitle(country)

save_figure_bundle(pics_output_folder, 'NOx emissions, tropomi vs wrf, THOFA, {}'.format(country))
#%% Plot Kuwait maps
country = 'Kuwait'
e_country_tropomi = extract_diag_by_country(e_nox_tropomi_ds, country)  # moles/ km2/hr
e_country_wrf = extract_diag_by_country(e_wrf_ds.E_NO, country).squeeze() # moles/ km2/hr

fig, axes = plt.subplots(nrows=1, ncols=2, subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(20, 10), constrained_layout=True)
contourf_levels = np.linspace(-2.5, 5, 80)
contourf_levels = np.linspace(e_country_tropomi.quantile(0.05), e_country_tropomi.quantile(0.95), 80)
plot_emis_map(e_country_tropomi, contourf_levels, ax=axes[0])
axes[0].set_extent([46.5, 49, 28.5, 30.5])#, crs=ccrs.PlateCarree())
plot_emis_map(e_country_wrf, contourf_levels, ax=axes[1])
axes[1].set_extent([46.5, 49, 28.5, 30.5])#, crs=ccrs.PlateCarree())
plt.suptitle(country)

save_figure_bundle(pics_output_folder, 'NOx emissions, tropomi vs wrf, THOFA, {}'.format(country))

#%% Plot Qatar maps
country = 'Qatar'
e_country_tropomi = extract_diag_by_country(e_nox_tropomi_ds.nox_no2, country)  # moles/ km2/hr
e_country_wrf = extract_diag_by_country(e_wrf_ds.E_NO, country).squeeze() # moles/ km2/hr

fig, axes = plt.subplots(nrows=1, ncols=2, subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(20, 10), constrained_layout=True)
contourf_levels = np.linspace(-2.5, 5, 80)
contourf_levels = np.linspace(e_country_tropomi.quantile(0.05), e_country_tropomi.quantile(0.95), 80)
plot_emis_map(e_country_tropomi, contourf_levels, ax=axes[0])
axes[0].set_extent([50, 53, 24.5, 26.5])#, crs=ccrs.PlateCarree())
plot_emis_map(e_country_wrf, contourf_levels, ax=axes[1])
axes[1].set_extent([50, 53, 24.5, 26.5])#, crs=ccrs.PlateCarree())
plt.suptitle(country)

save_figure_bundle(pics_output_folder, 'NOx emissions, tropomi vs wrf, THOFA, {}'.format(country))

#%% Plot Qatar maps without extraction
e_country_tropomi = e_nox_tropomi_ds.nox_no2
e_country_wrf = e_wrf_ds.E_NO.squeeze()

fig, axes = plt.subplots(nrows=1, ncols=2, subplot_kw={'projection': ccrs.PlateCarree()}, figsize=(20, 10), constrained_layout=True)
contourf_levels = np.linspace(-2.5, 5, 80)
contourf_levels = np.linspace(e_country_tropomi.quantile(0.05), e_country_tropomi.quantile(0.95), 80)
plot_emis_map(e_country_tropomi, contourf_levels, ax=axes[0])
axes[0].set_extent([50, 53, 24.5, 26.5])#, crs=ccrs.PlateCarree())
plot_emis_map(e_country_wrf, contourf_levels, ax=axes[1])
axes[1].set_extent([50, 53, 24.5, 26.5])#, crs=ccrs.PlateCarree())
plt.suptitle(country)
save_figure_bundle(pics_output_folder, 'NOx emissions, tropomi vs wrf, THOFA, {} zoom'.format(country))

axes[0].set_extent([49, 54, 23.5, 27.5])#, crs=ccrs.PlateCarree())
axes[1].set_extent([49, 54, 23.5, 27.5])#, crs=ccrs.PlateCarree())
axes[1].set_extent([50, 53, 24.5, 26.5])#, crs=ccrs.PlateCarree())
save_figure_bundle(pics_output_folder, 'NOx emissions, tropomi vs wrf, THOFA, {} zoom'.format(country))

#%%
plt.clf()
e_nox_by_country.transpose().to_pandas().plot.scatter('wrf', 'tropomi')
e_nox_by_country.to_ta
plt.legend()

#e_nox_by_country.transpose().to_pandas() # moles /hr
#e_nox_by_country.transpose().to_pandas() * 30 * 10**-9 # kt /hr


e_nox_by_country.transpose().to_pandas() * nox_mm * 10**-9 * (30*24)  # kt / month
e_nox_by_country.transpose().to_pandas() * nox_mm * 10**-9 * (24*365)  # kt / year

nh3_mm = 17  # g/mol
e_by_country_wrf.E_NH3.transpose().to_pandas() * nh3_mm * 10**-9 * (24*365)  # kt / year
co_mm = 28  # g/mol
e_by_country_wrf.E_CO.transpose().to_pandas() * co_mm * 10**-9 * (24*365)  # kt / year
#%%
plt.figure()
plt.clf()
plt.scatter(e_nox_by_country_tropomi, e_by_country_wrf.E_NO)

#%%
plt.figure()
e_nox_tropomi_ds.plot(vmin=da.quantile(0.05), vmax=da.quantile(0.95))  # x='XLONG', y='XLAT',  #,geo=True,rasterize=True,project=True)
#%%
plt.figure()
e_wrf_ds.E_NO.plot(vmin=da.quantile(0.05), vmax=da.quantile(0.95))  # x='XLONG', y='XLAT',  #,geo=True,rasterize=True,project=True)

#%%
e_nox_qatar_tropomi = extract_diag_by_country(e_nox_tropomi_ds, 'Qatar')

plt.figure()
e_nox_qatar_tropomi.plot(vmin=da.quantile(0.05), vmax=da.quantile(0.95))  # x='XLONG', y='XLAT',  #,geo=True,rasterize=True,project=True)

#%%

e_nox_tropomi_orig_ds = prep_tropomi_nox_emissions(False)  # emissions in original units

da = e_nox_tropomi_orig_ds
contourf_levels = np.linspace(-2.5, 5, 80)


#%% plot WRF
contourf_levels = np.linspace(-2.5, 5, 80)
ax = plot_emis_map(e_wrf_ds.E_CO.squeeze(), contourf_levels)
ax.set_extent([45, 60, 20, 35])#, crs=ccrs.PlateCarree())

#%% Compare VOC emissions

VOC_mm = 12*3+1*8  # g/mol  # 14 + x16

f_voc_wrf = VOC_mm * 10 ** -9 * (24 * 365)  # kt / year
e_voc_wrf = e_by_country_wrf.E_HC3 * f_voc_wrf  # kt / year

e_voc_wrf.transpose().to_pandas()

# in EDGAR 6.1, Total NMVOC 2018
#Turkey is 927 Kt
# Saudi 1783
# Israel 136
# Egypt 707