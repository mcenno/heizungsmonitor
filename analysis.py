from typing import Any
from sqlalchemy import create_engine, true
import pandas as pd
from datetime import timedelta
import yaml
import numpy as np
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go

# load yml file to dictionary
def read_cred(filename='credentials.yml'):
    with open(filename, "r") as stream:
        try:
            cred = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return(cred)

def read_data(cred, cols=['time', 'vorlauftemperatur']):
    # read data from db
    db_connection_str = f'mysql+pymysql://{cred["user"]}:{cred["pass"]}@{cred["host"]}/measurements'
    db_connection = create_engine(db_connection_str)
    colstring = ', '.join(cols)
    df = pd.read_sql(f'SELECT {colstring} FROM data', con=db_connection)
    db_connection.dispose()
    # convert from utc to local time
    df['time'] = df['time'].dt.tz_localize('utc').dt.tz_convert('Europe/Berlin')
    return(df)

def calc_derivative(df, xcol='time', ycol='vorlauftemperatur'):
    df['delta_x'] = (pd.to_datetime(df[xcol]) - 
                     pd.to_datetime(df[xcol].shift(1))).dt.total_seconds()/60.0
    df['delta_y'] = df[ycol] - df[ycol].shift(1)
    df['slope'] = df['delta_y'] / df['delta_x']
    return(df['slope'])

def temp_vs_verbrauch():
    cred = read_cred()
    df = read_data(cred, 
                   cols=['time', 
                         'aussentemperatur', 
                         'heizungsraum',
                         'total_energy_1'])

    # calculate aggregate data
    df_agg = pd.concat([
        (df.groupby(df['time'].dt.date)
           .agg(
              temperatur=('aussentemperatur', 'mean'),
              total_energy_min=('total_energy_1', 'min'),
              total_energy_max=('total_energy_1', 'max'),
              )
           .assign(Ort='Außentemperatur')
        ), 
        (df.groupby(df['time'].dt.date)
           .agg(
              temperatur=('heizungsraum', 'mean'),
              total_energy_min=('total_energy_1', 'min'),
              total_energy_max=('total_energy_1', 'max'),
              )
           .assign(Ort='Heizungsraum')
        )
    ]).sort_values(by=['time', 'Ort'])     

    df_agg['tagesverbrauch'] = df_agg['total_energy_max'] - df_agg['total_energy_min']

    # filter data
    df_agg = df_agg[(df_agg['tagesverbrauch'] > 1.0) & 
                    (df_agg['temperatur'].notna())]
    df_agg.drop(['total_energy_max', 'total_energy_min'], axis=1, inplace=True)
    cor_aussen       = df_agg[df_agg['Ort']=='Außentemperatur']['temperatur'].corr(df_agg[df_agg['Ort']=='Außentemperatur']['tagesverbrauch'])
    cor_heizungsraum = df_agg[df_agg['Ort']=='Heizungsraum']['temperatur'].corr(df_agg[df_agg['Ort']=='Heizungsraum']['tagesverbrauch'])
    print(f"Korrelation Heizungsraum/Verbrauch:     {cor_heizungsraum}")
    print(f"Korrelation Außentemperatur/Verbrauch:  {cor_aussen}")

    # plot data
    pio.renderers.default = "browser"
    fig = px.scatter(df_agg, x="temperatur", 
                             y="tagesverbrauch",
                             color="Ort",
                             trendline='ols',
                             labels={
                                'temperatur': 'Temperatur [°C]',
                                'tagesverbrauch': 'Energieverbrauch [kWh/Tag]'
                             })
    fig.show()

def plot_daily_hourly():
    # read data
    cred = read_cred()
    df = read_data(cred, 
                   cols=['time', 
                         'total_energy_1',
                         'total_energy_2'])
    
    # calculate hourly consumption averages
    df_hourly = (df.assign(date=df['time'].dt.date,
                           hour=df['time'].dt.hour)
                # first calculate deltas per day and hour
                 .groupby(['date', 'hour'])
                 .agg(max_wp=('total_energy_1', 'max'),
                      max_haus=('total_energy_2', 'max'))
                 .assign(max_wp_prev=lambda x: x['max_wp'].shift(1),
                         max_haus_prev=lambda x: x['max_haus'].shift(1),
                         delta_wp=lambda x: x['max_wp'] - x['max_wp_prev'],
                         delta_haus=lambda x: x['max_haus'] - x['max_haus_prev'])
                 .reset_index()
                 # then average the hours from all days
                 .groupby('hour')
                 .agg(wp_mean=('delta_wp', 'mean'),
                      haus_mean=('delta_haus', 'mean'))
                 .reset_index())
    
    df_daily = (df.assign(date=df['time'].dt.date)
                .groupby(['date'])
                .agg(max_wp=('total_energy_1', 'max'),
                     max_haus=('total_energy_2', 'max'))
                .assign(max_wp_prev=lambda x: x['max_wp'].shift(1),
                        max_haus_prev=lambda x: x['max_haus'].shift(1),
                        daily_wp=lambda x: x['max_wp'] - x['max_wp_prev'],
                        daily_haus=lambda x: x['max_haus'] - x['max_haus_prev'])
                .reset_index())
    
    # stack the two measurements ontop of each other for easier plotting
    # was needed for use with Plotly Express
    # df_hourly = pd.concat([
    #     df_hourly
    #     .assign(hour=df_hourly['hour'],
    #             kwh=df_hourly['wp_mean'],
    #             loc='wp'),
    #     df_hourly
    #     .assign(hour=df_hourly['hour'],
    #             kwh=df_hourly['haus_mean'],
    #             loc='haus')
    # ])
    # df_daily = pd.concat([
    #     df_daily
    #     .assign(date=df_daily['date'],
    #             kwh=df_daily['daily_wp'],
    #             loc='wp'),
    #     df_daily
    #     .assign(date=df_daily['date'],
    #             kwh=df_daily['daily_haus'],
    #             loc='haus')
    # ])
    
    pio.renderers.default = "browser"
    
    # Plotly Express can't easily do subplots
    # fig = go.Figure()
    # fig = px.bar(df_hourly, x='hour', y='kwh', 
    #              color='loc', 
    #              barmode='group')
    # fig.show()
    
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2)
    fig.add_trace(go.Bar(x=df_hourly['hour'], y=df_hourly['wp_mean']), row=1, col=1)
    fig.add_trace(go.Bar(x=df_hourly['hour'], y=df_hourly['haus_mean']), row=1, col=1)

fig.add_trace(go.Bar(x=df_daily['date'], y=df_daily['daily_wp']), row=1, col=2)
fig.add_trace(go.Bar(x=df_daily['date'], y=df_daily['daily_haus']), row=1, col=2)


# df = read_data(cred, 
#                cols=['time', 
#                      'vorlauftemperatur', 
#                      'warmwassertemperatur'])
# df['warmw_smo'] = df['warmwassertemperatur'].rolling(window=5, center=True).mean()
# df['vorlauf_deriv'] = calc_derivative(df.copy(), xcol='time', ycol='vorlauftemperatur')
# df['warmw_deriv'] = calc_derivative(df.copy(), xcol='time', ycol='warmwassertemperatur')
# s = abs(df['warmw_deriv']) <= 0.1
# df['warmw_deriv_clip'] = df['warmw_deriv'].where(s, other=np.nan)
# df['warmw_deriv_clip_smo'] = df['warmw_deriv_clip'].rolling(window=60, center=True, min_periods=55).mean()
# 
# 
# import plotly.graph_objects as go
# import plotly.io as pio
# pio.renderers.default = "browser"
# 
# fig = go.Figure()
#  
# #fig.add_trace(go.Line(x=df['time'], y=df['vorlauf_deriv'],
# #                     name="dT/dt (vorl)", yaxis='y'))
# fig.add_trace(go.Line(x=df['time'], y=df['warmw_deriv'],
#                      name="dT/dt (warmw)", yaxis='y'))
# fig.add_trace(go.Line(x=df['time'], y=df['warmw_deriv_clip'],
#                      name="dT/dt (warmw_deriv_clip)", yaxis='y'))
# fig.add_trace(go.Line(x=df['time'], y=df['warmw_deriv_clip_smo'],
#                      name="dT/dt (warmw_deriv_clip_smo)", yaxis='y'))
#  
# fig.add_trace(go.Scatter(x=df['time'], y=df['vorlauftemperatur'],
#                       name="vorlauf", yaxis="y2", opacity=0.5))
# fig.add_trace(go.Scatter(x=df['time'], y=df['warmwassertemperatur'],
#                       name="warmwasser", yaxis="y2", opacity=0.5))
# #fig.add_trace(go.Scatter(x=df['time'], y=df['warmw_smo'],
# #                      name="warmw_smo", yaxis="y2", opacity=0.5))
#  
# # Create axis objects
# fig.update_layout(
#     #create 1st y axis             
#     yaxis=dict(
#         title="Anstieg [Kelvin/min]",
#         titlefont=dict(color="#1f77b4"),
#         tickfont=dict(color="#1f77b4")),
#                    
#     #create 2nd y axis      
#     yaxis2=dict(title="Temperatur [°Celsius]",overlaying="y",
#                 side="right"))
#   
# fig.show()
# 