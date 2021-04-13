import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.collections as collections
from matplotlib.dates import date2num
import datetime as dt
import pathlib, os

from matplotlib.backends.backend_agg import RendererAgg
_lock = RendererAgg.lock

apptitle = 'IAB1-Arduino-HumiditySensorViewer'
st.set_page_config(page_title=apptitle, layout='wide')
st.title('Humidity Sensor Viewer')

CONFIG_PATH = r'C:\Users\User\Desktop\dimaghi\config.txt'
def load_data(path_config):
    with open(path_config, encoding='utf8') as f:
        lines = f.read().splitlines()
        for line in lines:
            mod = line.split(' ')

            if 'arduino' in  mod[0].lower():
                # print('Path dados arduino:\t',mod[-1])
                path_arduino = pathlib.Path(mod[-1])

                dirs = [e for e in path_arduino.iterdir() if e.is_dir()]
                dirs_names = [dir.name for dir in path_arduino.iterdir() if dir.is_dir()]
                # print(dirs)
                # print(dirs_names)

                arduino_dfs = {}


            if 'estacao' in mod[0].lower():
                # print('Path dados estação:\t', mod[-1])
                path_estacao = pathlib.Path(mod[-1])
                iab1_dfs = []
                for file in path_estacao.rglob('*.dat'):
                    # print(file)
                    iab1_dfs.append(pd.read_csv(file, skiprows=[0,2,3], na_values=['NAN'], parse_dates=['TIMESTAMP']))

                iab1_df = pd.concat(iab1_dfs)
                iab1_df.drop_duplicates(subset='TIMESTAMP', keep='first', inplace=True)
                iab1_df.reset_index(inplace=True)

    return iab1_df, dirs, dirs_names

def select_folder(dir_name, dirs):
    for folder in dirs:
        if folder.name == dir_name:
            # print(folder)
            folder_selected = folder
        else:
            pass
    return folder_selected

def read_arduino(folder):
    columns_name = ['ano','mes','dia','hora','minuto','segundo']
    filenames = []
    dfs = []

    for file in folder.rglob('*.txt'):
        filenames.append(file.name)
        df = pd.read_csv(file)

        n_sensors = len(df.columns) - len(columns_name)
        columns_name_sensors = columns_name + [f'sensor_{file.stem}_{i}' for i in range(n_sensors)]
        # print(columns_name_sensors)
        df.columns = columns_name_sensors

        df['date'] = df['ano'].astype(str) + '/' + df['mes'].astype(str) + '/' + df['dia'].astype(str)
        df['time'] = df['hora'].astype(str) + ':' + df['minuto'].astype(str) + ':' + df['segundo'].astype(str)
        df['TIMESTAMP'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        dfs.append(df)
    return dfs, filenames

def resample_data(dfs_arduino, filenames, iab1_df):
    dfs = []
    for df, name in zip(dfs_arduino, filenames):
        sensors_columnsName = df.columns[df.columns.str.contains('sensor')]

        df = df.groupby(by='TIMESTAMP').mean()[sensors_columnsName].reset_index()
        df.sort_values(by='TIMESTAMP', inplace=True)
        # df = df.resample(f'{arduino_resampleRate}').mean().reset_index()
        df_date = df.loc[(df['TIMESTAMP'].dt.date>=date_start)&
                         (df['TIMESTAMP'].dt.date<=date_end)].copy()
        # print(df_date.describe())
        dfs.append(df_date)
    return dfs

def stats_data(dfs_arduino, filenames):
    st.markdown(f'#### Begin: {date_start} | End: {date_end}')
    st.markdown('-------------------------------')
    # st.markdown(f'#### End: {date_end}')

    for df, name in zip(dfs_arduino, filenames):
        sensors_columnsName = df.columns[df.columns.str.contains('sensor')]

        print(df.describe())
        df.sort_values(by='TIMESTAMP', inplace=True)
        df.drop_duplicates(subset='TIMESTAMP', inplace=True)
        df.reset_index(inplace=True)
        # print(df.reset_index())
        diff = df['TIMESTAMP'].diff()

        index_gaps = diff.loc[diff>pd.Timedelta('00:02:00')].value_counts().sort_index().index
        gaps = (diff.loc[diff>pd.Timedelta('00:02:00')]-pd.Timedelta('00:02:00')).sum()
        print(gaps)

        total_date = df['TIMESTAMP'].max()-df['TIMESTAMP'].min()
        print(df['TIMESTAMP'].max()-df['TIMESTAMP'].min())
        print(gaps/total_date)
        # st.markdown('**GAPS:**')
        st.markdown(f'Percentage of gaps in {name}: **{gaps/total_date*100:.2f}** %')
        # print(df.reset_index(inplace=True)['TIMESTAMP'][-1]-df.reset_index(inplace=True)['TIMESTAMP'][0])
        # print(diff.loc[diff>pd.Timedelta('00:02:00')].value_counts().sort_index())
        # print(index_gaps)

        # fig, ax1 = plt.subplots()
        # ax1.plot(df['TIMESTAMP'], df[sensors_columnsName])

        # start = df.loc[df['TIMESTAMP'].diff()>pd.Timedelta('00:02:00'),'TIMESTAMP']
        # end = df.loc[df['TIMESTAMP'].diff()>pd.Timedelta('00:02:00'),'TIMESTAMP']-diff.loc[diff>pd.Timedelta('00:02:00')]+pd.Timedelta('00:02:00')



        # for s, e in zip(start, end):
        #     ax1.axvspan(s,e,facecolor='red', alpha=0.5)
        # st.pyplot(plt)


def plot(dfs, filenames, iab1_df):
    for df, name in zip(dfs, filenames):
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        sensors_columnsName = df.columns[df.columns.str.contains('sensor')]

        df = df.groupby(by='TIMESTAMP').mean()[sensors_columnsName]
        df2 = df.reset_index()

        diff = df2['TIMESTAMP'].diff()
        start = df2.loc[df2['TIMESTAMP'].diff()>pd.Timedelta('00:02:00'),'TIMESTAMP']
        end = df2.loc[df2['TIMESTAMP'].diff()>pd.Timedelta('00:02:00'),'TIMESTAMP']-diff.loc[diff>pd.Timedelta('00:02:00')]+pd.Timedelta('00:02:00')

        if arduino_interpolate:
            df = df.resample(f'{arduino_resampleRate}').mean().interpolate().reset_index()
        else:
            df = df.resample(f'{arduino_resampleRate}').mean().reset_index()
        iab1_df_date = iab1_df[(iab1_df['TIMESTAMP'].dt.date>=date_start)&
                               (iab1_df['TIMESTAMP'].dt.date<=date_end)].copy()
        iab1_df_resample = iab1_df_date.set_index('TIMESTAMP')['Rain_mm_Tot'].resample(f'{iab1_resampleRate}').sum().reset_index()
        # iab1_df_resample.reset_index(inplace=True)
        # print(iab1_df_resample)

        df_date = df.loc[(df['TIMESTAMP'].dt.date>=date_start)&
                         (df['TIMESTAMP'].dt.date<=date_end)].copy().reset_index()


        # print(df_date[sensors_columnsName[0]].notna())
        ax1.plot(df_date['TIMESTAMP'], df_date[sensors_columnsName])
        # print(df_date.loc[10,'TIMESTAMP'])
        # ax1.axvspan(dt.datetime(2021,1,5),dt.datetime(2021,1,13), facecolor='red', alpha=0.5)
        if gap_checkbox:
            for s, e in zip(start, end):
                ax1.axvspan(s,e,facecolor=f'{gap_color}', alpha=0.5)

        ax1.legend(sensors_columnsName, fontsize=6,loc='upper left')

        ax2.bar(iab1_df_resample['TIMESTAMP'], iab1_df_resample['Rain_mm_Tot'], color='black', alpha=0.7, width=0.1)
        plt.xlim((date_start,date_end))

        fig.autofmt_xdate()
        plt.grid()

        st.pyplot(plt)

iab1_df, arduino_dirs, name_dirs = load_data(path_config=CONFIG_PATH)

sidebar = st.sidebar
sidebar.markdown('# Configurations')
select_arduino = sidebar.selectbox('Select the ARDUINO folder:', name_dirs)

date_start = sidebar.date_input('Start:')
date_end = sidebar.date_input('End:')

iab1_resampleRate = sidebar.select_slider('Resample IAB1 (Rain):', options=['10min', '30min','1h','3h','6h','12h','1d'],value='12h')
arduino_resampleRate = sidebar.select_slider('Resample Arduino data:', options=['10min', '30min','1h','3h','6h','12h','1d'])
arduino_interpolate = sidebar.checkbox('Interpolate after resample (Arduino)')

# gap_spacer1, gap_spacer2 = sidebar.beta_columns(2)
# with gap_spacer1:
gap_checkbox = sidebar.checkbox('View Gaps')
# with gap_spacer2:
gap_color = sidebar.color_picker('Gap color')

folder = select_folder(dir_name=select_arduino, dirs=arduino_dirs)
dfs_arduino, filenames = read_arduino(folder=folder)

dfs_arduino2 = resample_data(dfs_arduino=dfs_arduino, filenames=filenames, iab1_df=iab1_df)


row1_spacer1, row1_spacer_2 = st.beta_columns((2,1))
# row2_spacer1, row2_spacer_2 = st.beta_columns((2,1))

with row1_spacer1:
    st.markdown('## Graphs')
# with row2_spacer1:
    plot(dfs=dfs_arduino,filenames=filenames, iab1_df=iab1_df)

with row1_spacer_2:
    st.markdown('## Stats')
# with row2_spacer_2:
    stats_data(dfs_arduino=dfs_arduino2, filenames=filenames)
sidebar.markdown('[Github](https://github.com/alexnaoki/iab1_arduino-viewer)')
