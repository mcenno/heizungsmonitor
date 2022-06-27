from sqlalchemy import create_engine, true
import pandas as pd
from datetime import timedelta
import yaml
import numpy as np

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

cred = read_cred()
df = read_data(cred, 
               cols=['time', 
                     'vorlauftemperatur', 
                     'warmwassertemperatur'])
df['warmw_smo'] = df['warmwassertemperatur'].rolling(window=5, center=True).mean()
df['vorlauf_deriv'] = calc_derivative(df.copy(), xcol='time', ycol='vorlauftemperatur')
df['warmw_deriv'] = calc_derivative(df.copy(), xcol='time', ycol='warmwassertemperatur')
s = abs(df['warmw_deriv']) <= 0.1
df['warmw_deriv_clip'] = df['warmw_deriv'].where(s, other=np.nan)
df['warmw_deriv_clip_smo'] = df['warmw_deriv_clip'].rolling(window=60, center=True, min_periods=55).mean()


import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = "browser"

fig = go.Figure()
 
#fig.add_trace(go.Line(x=df['time'], y=df['vorlauf_deriv'],
#                     name="dT/dt (vorl)", yaxis='y'))
fig.add_trace(go.Line(x=df['time'], y=df['warmw_deriv'],
                     name="dT/dt (warmw)", yaxis='y'))
fig.add_trace(go.Line(x=df['time'], y=df['warmw_deriv_clip'],
                     name="dT/dt (warmw_deriv_clip)", yaxis='y'))
fig.add_trace(go.Line(x=df['time'], y=df['warmw_deriv_clip_smo'],
                     name="dT/dt (warmw_deriv_clip_smo)", yaxis='y'))
 
fig.add_trace(go.Scatter(x=df['time'], y=df['vorlauftemperatur'],
                      name="vorlauf", yaxis="y2", opacity=0.5))
fig.add_trace(go.Scatter(x=df['time'], y=df['warmwassertemperatur'],
                      name="warmwasser", yaxis="y2", opacity=0.5))
#fig.add_trace(go.Scatter(x=df['time'], y=df['warmw_smo'],
#                      name="warmw_smo", yaxis="y2", opacity=0.5))
 
# Create axis objects
fig.update_layout(
    #create 1st y axis             
    yaxis=dict(
        title="Anstieg [Kelvin/min]",
        titlefont=dict(color="#1f77b4"),
        tickfont=dict(color="#1f77b4")),
                   
    #create 2nd y axis      
    yaxis2=dict(title="Temperatur [°Celsius]",overlaying="y",
                side="right"))
  
fig.show()
