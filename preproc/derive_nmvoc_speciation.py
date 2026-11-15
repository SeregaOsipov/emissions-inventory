import pandas as pd
import re
#%%

fp = '/work/mm0062/b302074/workspace/python/hermesv3_gr/preproc/VOC_split_SHIP.csv'
df = pd.read_table(fp, sep=';')
df = df.transpose()

headers = df.iloc[0]
df = df[1:]
df.columns = headers

#%% Plugin numbers instead of vocXX for the speciation of the NMVOCs

# shipping from HTAPv2
profile = 'E008;nox_no2;co;so2;0;voc22;0;0;voc02;0.95*voc01+voc03+voc04+0.4*voc09+0.69*voc18;0.05*voc01+voc05+0.43*voc06+0.31*voc18;0.57*voc06+voc17+voc19;voc21;0;voc23;voc07;voc12;voc08;0.44*voc24;0.56*voc24;0.293*voc13+voc14;voc16+voc17;pm10;(pm25-oc-bc)*0.3704;(pm25-oc-bc)*0.0926;bc*0.8;bc*0.2;oc*0.8;oc*0.2;0;0;(pm25-oc-bc)*0.4296;(pm25-oc-bc)*0.1074'

# replace the vocXX with the weight
for header in headers:
    profile = re.sub(header, '{:.6f}*nmvoc'.format(df[header][0]), profile)

print(profile)