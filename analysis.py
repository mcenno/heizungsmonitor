from sqlalchemy import create_engine
import pandas as pd
from datetime import timedelta

# read data from db
db_connection_str = 'mysql+pymysql://remoteuser:utvXrWSVtxrz6S4BzU$@192.168.178.37/measurements'
db_connection = create_engine(db_connection_str)
df = pd.read_sql('SELECT time, vorlauftemperatur FROM data', con=db_connection)
db_connection.dispose()

# calculate deltas
df['delta_time'] = (pd.to_datetime(df['time']) - 
                    pd.to_datetime(df['time'].shift(1))).dt.total_seconds()/60.0
df['delta_temp'] = df['vorlauftemperatur'] - df['vorlauftemperatur'].shift(1)
df['slope'] = df['delta_temp'] / df['delta_time']

#df.plot(x='time', y=['slope'])


import plotly.graph_objects as go
 
fig = go.Figure()
 
fig.add_trace(go.Line(x=df['time'], y=df['slope'],
                     name="slope", yaxis='y'))
 
fig.add_trace(go.Scatter(x=df['time'], y=df['vorlauftemperatur'],
                      name="vorlauf", yaxis="y2", opacity=0.5))
 
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
 
# title
fig.update_layout(
    title_text="Geeksforgeeks - Three y-axes",
    width=800,
)
 
fig.show()