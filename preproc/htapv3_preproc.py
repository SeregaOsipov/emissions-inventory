#!/usr/bin/env python

# Copyright 2018 Earth Sciences Department, BSC-CNS
#
# This file is part of HERMESv3_GR.
#
# HERMESv3_GR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HERMESv3_GR is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HERMESv3_GR. If not, see <http://www.gnu.org/licenses/>.

import xarray as xr
import os
import pandas as pd
from hermesv3_gr.tools.netcdf_tools import extract_vars, write_netcdf
from hermesv3_gr.tools.coordinates_tools import create_bounds
# ============== README ======================
"""
Only HTAPv3 VOCs are implemented at the moment
HTAPv3 total VOCs are split into the 25 voc according to the speciation file provided

reference: https://edgar.jrc.ec.europa.eu/dataset_htap_v3
downloading website: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/htap_v3/
Besides citing HERMESv3_GR, users must also acknowledge the use of the corresponding emission inventories in their works

run python like this:
cd /work/mm0062/b302074/Data/emissions/HTAP/htap_v3/gridmaps_01x01/fluxes
gogomamba
mamba activate py37_hermes 
python -u $HERMES3_OLD/preproc/htapv3_preproc.py
"""

# ============== CONFIGURATION PARAMETERS ======================
INPUT_PATH = '/work/mm0062/b302074/Data/emissions/HTAP/htap_v3/gridmaps_01x01/fluxes/'  # levante
# INPUT_PATH = '/Users/osipovs/Data/emissions/HTAP/htap_v3/gridmaps_01x01/fluxes/'  # local
OUTPUT_PATH = INPUT_PATH + '/hermes_pp/'

INPUT_NAME = 'edgar_HTAPv3_<year>_<pollutant>.nc'

LIST_YEARS = [2017,]

HTAP_v3_VOC_SPECIATION_PATH = '/work/mm0062/b302074/workspace/python/hermesv3_gr/preproc/nmvoc/NMVOC_speciation_HTAP_v3.xls'  # levante
# HTAP_v3_VOC_SPECIATION_PATH = '/Users/osipovs/PycharmProjects/hermesv3_gr/preproc/nmvoc/NMVOC_speciation_HTAP_v3.xls'  # local
#%%


if __name__ == '__main__':
    for year in LIST_YEARS:
        # AP are not implemented (ported from v2) yet
        # for pollutant_dict in get_pollutant_dict().items():
        #     for current_sector in get_sector_dict()[pollutant_dict[0]]['month']:
        #         input_name_aux = INPUT_NAME.replace('<sector>', current_sector)
        #         input_name_aux = input_name_aux.replace('<year>', str(y))
        #         input_name_aux = input_name_aux.replace('<pollutant>', pollutant_dict[1])
        #         file_list = [os.path.join(INPUT_PATH, input_name_aux.replace('<month>', str(aux_month)))
        #                      for aux_month in range(1, 13)]
        #
        #         do_transformation(file_list, os.path.join(OUTPUT_PATH, 'monthly_mean'), pollutant_dict[0],
        #                           current_sector, y)
        #     # annual inventories
        #     for current_sector in get_sector_dict()[pollutant_dict[0]]['year']:
        #         if current_sector[0:3] == 'AIR':
        #             input_name_aux = INPUT_NAME_AIR
        #         else:
        #             input_name_aux = INPUT_NAME_SHIPS
        #         input_name_aux = input_name_aux.replace('<sector>', current_sector)
        #         input_name_aux = input_name_aux.replace('<year>', str(y))
        #         input_name_aux = input_name_aux.replace('<pollutant>', pollutant_dict[1])
        #         input_name_aux = os.path.join(INPUT_PATH, input_name_aux)
        #
        #         do_transformation_annual(input_name_aux, os.path.join(OUTPUT_PATH, 'yearly_mean', ), pollutant_dict[0], current_sector, y)

        input_name_aux = INPUT_NAME
        input_name_aux = input_name_aux.replace('<pollutant>', 'NMVOC')
        input_name_aux = input_name_aux.replace('<year>', str(year))
        emissions_file_path = os.path.join(INPUT_PATH, 'NMVOC/', input_name_aux)
        htapv3_ds = xr.open_dataset(emissions_file_path)

        c_lats, c_lons = extract_vars(emissions_file_path, ['lat', 'lon'])

        # get the VOC speciation for HTAPv3
        voc_speciation_df = pd.read_excel(HTAP_v3_VOC_SPECIATION_PATH, skiprows=2)#, header=)
        sector_codes = voc_speciation_df['SECTOR CODE'].unique()
        sectors = voc_speciation_df['SECTOR NAME'].unique()
        vocs = voc_speciation_df.filter(regex=("voc.*")).columns.to_list()
        print('SPECIATION IS NOT COUNTRY SPECIFIC. DERIVE THE SPATIAL MAP')
        # TODO:: The speciation is country specific. But now treat everything as region Other, but remember that Turkey falls into region Europe
        # Have to include the region World, due to international shipping and aviations
        df = voc_speciation_df
        voc_speciation_me_df = df.loc[df['REGION'].isin(['Other', 'World'])]

        for sector, sector_code in zip(sectors, sector_codes):  # this is monthly
            # prepare the keys
            nc_key_template = 'HTAPv3_{}_'.format(sector_code.split('_')[1].replace('.','_'))
            result = [key for key in htapv3_ds.data_vars if key.startswith(nc_key_template)]
            if len(result) != 1:
                raise Exception('The key has to be unique')
            nc_var_key = result[0]
            print('{} {} {}'.format(sector, sector_code, nc_var_key))

            df = voc_speciation_me_df
            speciation_df = df.loc[df['SECTOR CODE'] == sector_code].reset_index()[vocs]
            speciation_ds = speciation_df.transpose().rename({0: 'voc_speciation'}, axis='columns').to_xarray()
            speciation_ds = speciation_ds.rename({'index': 'voc'})

            for month in range(1, 13):
                month_index = month - 1
                print('Month {}'.format(month))

                sector_ds = htapv3_ds[nc_var_key][month_index]
                speciated_vocs_ds = speciation_ds.voc_speciation * sector_ds

                for voc in vocs:
                    print(voc)
                    pollutant = voc

                    data_aux = {'name': nc_var_key, 'data': speciated_vocs_ds.sel(voc=voc).data}
                    data_aux['data'] = data_aux['data'].reshape((1,) + data_aux['data'].shape)
                    data_aux['name'] = voc
                    data_aux['units'] = 'kg m-2 s-1'
                    global_attributes = {
                        'title': 'HTAPv3 inventory for the sector code {}, sector {} and pollutant {}'.format(sector_code, sector, pollutant),
                        'Conventions': 'CF-1.6',
                        'institution': 'European Commission, Joint Research Centre (JRC)',
                        'source': 'HTAPv3',
                        'history': 'Re-writing of the HTAPv2 input to follow the CF 1.6 conventions;',
                        'comment': 'Re-writing done by Sergey Osipov (sergey.osipvo@kaust.edu.sa) from KAUST',
                    }

                    out_path = os.path.join(OUTPUT_PATH, 'monthly_mean')
                    sector_label = sector.lower().replace(' ', '_')  # have to provide file path friendly sector name. It will be used in EI as well
                    out_path_aux = os.path.join(out_path, pollutant + '_' + sector_label)
                    if not os.path.exists(out_path_aux):
                        os.makedirs(out_path_aux)

                    out_path_aux = os.path.join(out_path_aux, '{0}_{1}{2}.nc'.format(pollutant, year, str(month).zfill(2)))
                    print(out_path_aux)
                    write_netcdf(out_path_aux, c_lats['data'], c_lons['data'], [data_aux],
                                 boundary_latitudes=create_bounds(c_lats['data']),
                                 boundary_longitudes=create_bounds(c_lons['data']), global_attributes=global_attributes, )

print('DONE')

#%% list the sectors to paste into EI
voc_speciation_df = pd.read_excel(HTAP_v3_VOC_SPECIATION_PATH, skiprows=2)#, header=)
sectors = voc_speciation_df['SECTOR NAME'].unique()

for sector in sectors:  # this is monthly
    sector_label = sector.lower().replace(' ', '_')  # have to provide file path friendly sector name. It will be used in EI as well
    print(sector_label)

# the output

# domestic_aviation
# energy
# industry
# fugitive
# solvents
# road_transport
# domestic_shipping
# other_ground_transport
# residential
# waste
# agricultural_waste_burning
# agriculture_livestock
# agricultural_crops
# international_shipping
# international_aviation
#%%
