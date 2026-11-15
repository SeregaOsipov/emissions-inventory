import os
import subprocess

from cdo import Cdo
from netCDF4 import Dataset

'''
Sectors are listed here: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v81_FT2022_AP_new/_readme.html
Compared to version below, These sectors were missing: ENF, IDE, N2O, and these are extra: NMM, FOO_PAR, NEU
'''

EDGAR_GHG_IPCC_SECTOR_DICT = {  # https://edgar.jrc.ec.europa.eu/readme/v80_ft2022_ghg_readme.txt; https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v80_FT2022_GHG/CH4/
    "IPCC_4C_4D": "AGS",
    "IPCC_4F": "AWB",
    "IPCC_2B": "CHE",
    "IPCC_1A1a": "ENE",
    "IPCC_4A": "ENF",
    "IPCC_7B_7C": "IDE", #
    "IPCC_1A2": "IND",
    "IPCC_2C1a_2C1c_2C1d_2C1e_2C1f_2C2": "IRO",
    #"IPCC_2C3_2C4_2C5": "NFE",
    "IPCC_4B": "MNM",
    "IPCC_2A": "NMM",  # sector has been added to accomodate CO2
    #"IPCC_4D3": "N2O",
    # "IPCC_1B1a_1B2a1_1B2a2_1B2a3_1B2a4_1B2c": "PRO",  # This was lumped from PRO_COAL, PRO_GAS, PRO_OIL
    "IPCC_1B1a": "PRO_COAL",
    "IPCC_7A": "PRO_FFF",
    "IPCC_1B2c": "PRO_GAS",
    "IPCC_1B2a1_1B2a2_1B2a3_1B2a4": "PRO_OIL",
    #"IPCC_3": "PRU_SOL",
    "IPCC_1A4": "RCO",
    "IPCC_1A1b_1A1c_1A5b1_1B1b_1B2a5_1B2a6_1B2b5_2C1b": "REF_TRF",
    "IPCC_6C": "SWD_INC",
    "IPCC_6A_6D": "SWD_LDF",
    "IPCC_1A3a_CDS": "TNR_Aviation_CDS",
    "IPCC_1A3a_CRS": "TNR_Aviation_CRS",
    "IPCC_1A3a_LTO": "TNR_Aviation_LTO",
    "IPCC_1A3a_SPS": "TNR_Aviation_SPS",
    "IPCC_1A3c_1A3e": "TNR_Other",
    "IPCC_1A3d_1C2": "TNR_Ship",
    "IPCC_1A3b": "TRO",  # Can be split into Resuspension and No-Resuspension types
    # "IPCC_1A3b_noRES": "TRO_noRES",
    # "IPCC_1A3b_RES": "TRO_RES",
    "IPCC_6B": "WWT",
}

EDGAR_AP_IPCC_SECTOR_DICT = {  # https://edgar.jrc.ec.europa.eu/readme/v81_ft2022_ap_readme.txt; https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/v81_FT2022_AP_new/
    "IPCC_4C_4D": "AGS",
    "IPCC_4F": "AWB",
    "IPCC_2B": "CHE",
    "IPCC_1A1a": "ENE",
    "IPCC_4A": "ENF", #
#    "IPCC_7B_7C": "IDE",
    "IPCC_1A2": "IND",
    "IPCC_2C1a_2C1c_2C1d_2C1e_2C1f_2C2": "IRO",
    "IPCC_2C3_2C4_2C5": "NFE",
    "IPCC_4B": "MNM",
#    "IPCC_4D3": "N2O",
    #"IPCC_1B1a_1B2a1_1B2a2_1B2a3_1B2a4_1B2c": "PRO",  # This was lumped from PRO_COAL, PRO_GAS, PRO_OIL
    "IPCC_1B1a": "PRO_COAL",
    "IPCC_1B2c": "PRO_GAS",
    "IPCC_1B2a1_1B2a2_1B2a3_1B2a4": "PRO_OIL",
    "IPCC_7A": "PRO_FFF",
    "IPCC_3": "PRU_SOL",
    "IPCC_2D": "FOO_PAP",
    "IPCC_1A4": "RCO",
    "IPCC_1A1b_1A1c_1A5b1_1B1b_1B2a5_1B2a6_1B2b5_2C1b": "REF_TRF",
    "IPCC_6C": "SWD_INC",
    "IPCC_6A_6D": "SWD_LDF",
    "IPCC_1A3a_CDS": "TNR_Aviation_CDS",
    "IPCC_1A3a_CRS": "TNR_Aviation_CRS",
    "IPCC_1A3a_LTO": "TNR_Aviation_LTO",
    "IPCC_1A3a_SPS": "TNR_Aviation_SPS",
    "IPCC_1A3c_1A3e": "TNR_Other",
    "IPCC_1A3d_1C2": "TNR_Ship",
    "IPCC_1A3b": "TRO",  # Can be split into Resuspension and No-Resuspension types
    # "IPCC_1A3b_noRES": "TRO_noRES",
    # "IPCC_1A3b_RES": "TRO_RES",
    "IPCC_6B": "WWT",
}

EDGAR_IPCC_SECTOR_DICT_OLD = {  # whatever the version was used prior to running v6.1
    "IPCC_1A1a": "ENE",
    "IPCC_1A1b_1A1c_1A5b1_1B1b_1B2a5_1B2a6_1B2b5_2C1b": "REF_TRF",
    "IPCC_1A2": "IND",
    "IPCC_1A3a_CDS": "TNR_Aviation_CDS",
    "IPCC_1A3a_CRS": "TNR_Aviation_CRS",
    "IPCC_1A3a_LTO": "TNR_Aviation_LTO",
    # TODO: add 1A3a_SPS, Aviation supersonic, see table https://edgar.jrc.ec.europa.eu/overview.php?v=50_AP
    "IPCC_1A3b_noRES": "TRO_noRES",
    "IPCC_1A3b_RES": "TRO_RES",
    "IPCC_1A3c_1A3e": "TNR_Other",
    "IPCC_1A3d_1C2": "TNR_Ship",
    "IPCC_1A4": "RCO",
    "IPCC_1B1a_1B2a1_1B2a2_1B2a3_1B2a4_1B2c": "PRO",
    "IPCC_2A": "NMM",
    "IPCC_2B": "CHE",
    "IPCC_2C1a_2C1c_2C1d_2C1e_2C1f_2C2": "IRO",
    "IPCC_2C3_2C4_2C5": "NFE",
    "IPCC_2D": "FOO_PAP",
    "IPCC_2G": "NEU",
    "IPCC_3": "PRU_SOL",
    "IPCC_4B": "MNM",
    "IPCC_4C_4D": "AGS",
    "IPCC_4F": "AWB",
    "IPCC_6A_6D": "SWD_LDF",
    "IPCC_6B": "WWT",
    "IPCC_6C": "SWD_INC",
    "IPCC_7A": "FFF"
}


EDGAR_EIGHT_SECTORS = 'AGRICULTURE, FUEL_EXPLOITATION, IND_PROCESSES, TRANSPORT, BUILDINGS, IND_COMBUSTION, POWER_INDUSTRY, WASTE'.split(', ')
EDGAR_GHG_IPCC_SECTORS = [EDGAR_GHG_IPCC_SECTOR_DICT[ipcc] for ipcc in list(EDGAR_GHG_IPCC_SECTOR_DICT.keys())]
EDGAR_AP_IPCC_SECTORS = [EDGAR_AP_IPCC_SECTOR_DICT[ipcc] for ipcc in list(EDGAR_AP_IPCC_SECTOR_DICT.keys())]


def unzip_edgar_files(year, pollutants, sectors, INPUT_PATH, archive_fp_template):
    print('Run the script below in the bash once to extract the archives')
    for pollutant in pollutants:
        for sector in sectors:  # ipcc in list(ipcc_to_sector_dict().keys()):
            # sector = ipcc_to_sector_dict()[ipcc]
            archive_file_path = os.path.join(INPUT_PATH, archive_fp_template.replace('<pollutant>', pollutant).replace('<sector>', sector).replace('<year>', str(year)))
            print('unzip -o {} -d {}'.format(archive_file_path, os.path.dirname(archive_file_path)))
            result = subprocess.run(['unzip', '-o', archive_file_path, '-d', os.path.dirname(archive_file_path)], capture_output=True, text=True)
            print(result.stdout)


def write_netcdf(output_name_path, data, data_atts, center_lats, center_lons, grid_cell_area, year, sector, month=None):
    from hermesv3_gr.tools.netcdf_tools import create_bounds

    # Creating NetCDF & Dimensions
    print('out: {}'.format(output_name_path))
    nc_output = Dataset(output_name_path, mode='w', format="NETCDF4")
    nc_output.createDimension('nv', 2)
    nc_output.createDimension('lon', center_lons.shape[0])
    nc_output.createDimension('lat', center_lats.shape[0])
    nc_output.createDimension('time', None)

    # TIME
    time = nc_output.createVariable('time', 'd', ('time',), zlib=True)
    # time.units = "{0} since {1}".format(tstep_units, global_atts['Start_DateTime'].strftime('%Y-%m-%d %H:%M:%S'))
    if month is None:
        time.units = "years since {0}-01-01 00:00:00".format(year)
    else:
        time.units = "months since {0}-{1}-01 00:00:00".format(year, str(month).zfill(2))
    time.standard_name = "time"
    time.calendar = "gregorian"
    time.long_name = "time"
    time[:] = [0]

    # LATITUDE
    lat = nc_output.createVariable('lat', 'f', ('lat',), zlib=True)
    lat.bounds = "lat_bnds"
    lat.units = "degrees_north"
    lat.axis = "Y"
    lat.long_name = "latitude"
    lat.standard_name = "latitude"
    lat[:] = center_lats

    lat_bnds = nc_output.createVariable('lat_bnds', 'f', ('lat', 'nv',), zlib=True)
    lat_bnds[:] = create_bounds(center_lats)

    # LONGITUDE
    lon = nc_output.createVariable('lon', 'f', ('lon',), zlib=True)
    lon.bounds = "lon_bnds"
    lon.units = "degrees_east"
    lon.axis = "X"
    lon.long_name = "longitude"
    lon.standard_name = "longitude"
    lon[:] = center_lons

    lon_bnds = nc_output.createVariable('lon_bnds', 'f', ('lon', 'nv',), zlib=True)
    lon_bnds[:] = create_bounds(center_lons)

    # VARIABLE
    nc_var = nc_output.createVariable(data_atts['long_name'], 'f', ('time', 'lat', 'lon',), zlib=True)
    nc_var.units = data_atts['units']
    nc_var.long_name = data_atts['long_name']
    nc_var.coordinates = data_atts['coordinates']
    nc_var.grid_mapping = data_atts['grid_mapping']
    nc_var.cell_measures = 'area: cell_area'
    nc_var[:] = data.reshape((1,) + data.shape)

    # CELL AREA
    cell_area = nc_output.createVariable('cell_area', 'f', ('lat', 'lon',))
    cell_area.long_name = "area of the grid cell"
    cell_area.standard_name = "area"
    cell_area.units = "m2"
    cell_area[:] = grid_cell_area

    # CRS
    crs = nc_output.createVariable('crs', 'i')
    crs.grid_mapping_name = "latitude_longitude"
    crs.semi_major_axis = 6371000.0
    crs.inverse_flattening = 0

    nc_output.setncattr('title', 'EDGARv5.0_AP inventory for the sector {0} and pollutant {1}'.format(sector,  data_atts['long_name']), )
    nc_output.setncattr('Conventions', 'CF-1.6', )
    nc_output.setncattr('institution', 'JRC', )
    nc_output.setncattr('source', 'EDGARv5.0_AP', )
    nc_output.setncattr('comment', 'Re-writing done by Sergey Osipov (sergey.osipov@kaust.edu.sa) from KAUST', )

    nc_output.close()


def get_input_name(pollutant, LIST_POLLUTANTS, INPUT_NAME, INPUT_PATH):
    """
    Gets the path for the input file name

    :param pollutant: Name of the pollutant
    :type pollutant: str

    :return: Path to the input file
    :rtype: str
    """

    if pollutant in LIST_POLLUTANTS:
        file_name = INPUT_NAME.replace('<pollutant>', pollutant)
    else:
        raise ValueError('Pollutant {0} not in pollutant list'.format(pollutant))

    return os.path.join(INPUT_PATH, file_name)
