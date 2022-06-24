import mariadb
import pandas as pd
import sys
import yaml
import datetime
from sqlalchemy import create_engine, true
from itertools import product
from struct import pack, unpack
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from time import sleep

# registers we want to read
# see documentation at https://b2b.orno.pl/download-resource/26064/
regs = [
    {'quantity': 'frequency',    'reg': 0x014, 'size': 2},
    {'quantity': 'l1_voltage',   'reg': 0x00e, 'size': 2},
    {'quantity': 'l2_voltage',   'reg': 0x010, 'size': 2},
    {'quantity': 'l3_voltage',   'reg': 0x012, 'size': 2},
    {'quantity': 'l1_current',   'reg': 0x016, 'size': 2},
    {'quantity': 'l2_current',   'reg': 0x018, 'size': 2},
    {'quantity': 'l3_current',   'reg': 0x01a, 'size': 2},
    {'quantity': 'total_power',  'reg': 0x01c, 'size': 2},
    {'quantity': 'l1_power',     'reg': 0x01e, 'size': 2},
    {'quantity': 'l2_power',     'reg': 0x020, 'size': 2},
    {'quantity': 'l3_power',     'reg': 0x022, 'size': 2},
    {'quantity': 'total_energy', 'reg': 0x100, 'size': 2},
    {'quantity': 'l1_energy',    'reg': 0x102, 'size': 2},
    {'quantity': 'l2_energy',    'reg': 0x104, 'size': 2},
    {'quantity': 'l3_energy',    'reg': 0x106, 'size': 2},
       ]

# Meter IDs on the modbus. Once set to 1 and 2, done.
IDs = [1, 2]

# definition of temperature sensors
thermometers = {
                'aussentemperatur':    '28-00000418acd6',
                'vorlauftemperatur':   '10-0008027f54a6',
                'ruecklauftemperatur': '10-0008027f5818',
                'warmwassertemperatur': '28-6757b90164ff',
                'zirkulationsruecklauf': '28-1704b20164ff'
                }

# connect to Modbus
mbclient = ModbusClient(method='rtu', 
                        port='/dev/ttyUSB0', 
                        baudrate=9600,
                        bytesize=8, 
                        stopbits=1,
                        parity='E',
                        timeout=1)
mbclient.connect()

# connect to MariaDB
try:
    conn = mariadb.connect(user="remoteuser",
                           password="utvXrWSVtxrz6S4BzU$",
                           host="192.168.178.37",
                           port=3306,
                           database="measurements")
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)
cur = conn.cursor()

# load yml file to dictionary
def read_cred(filename='/home/pi/heizungsmonitor/credentials.yml'):
    with open(filename, "r") as stream:
        try:
            cred = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return(cred)

def read_last(cred):
    # read data from db
    db_connection_str = f'mysql+pymysql://{cred["user"]}:{cred["pass"]}@{cred["host"]}/measurements'
    db_connection = create_engine(db_connection_str)
    row = pd.read_sql('select * from data order by time desc limit 1', 
                      con=db_connection)
    db_connection.dispose()
    # convert from utc to local time
    row['time'] = row['time'].dt.tz_localize('utc').dt.tz_convert('Europe/Berlin')
    return(row)

# read data from modbus
def read_modbus(mbclient, id, q):
    read = mbclient.read_holding_registers(
               address=q['reg'], 
               count=q['size'], 
               unit=id) 
    data = unpack('f', pack('<HH', read.registers[1], read.registers[0]))[0]
    # function must not be called in too quick succession
    # make sure we wait a little before the next call
    sleep(0.05)
    return(data)

# read temperatures
def read_temp(w1_slave):
    file = open('/sys/bus/w1/devices/' + str(w1_slave) + '/w1_slave')
    filecontent = file.read()
    file.close()
    stringvalue = filecontent.split("\n")[1].split(" ")[9]
    temperature = float(stringvalue[2:]) / 1000
    return(temperature)

# start with current time stamp
utcnow = datetime.datetime.now(datetime.timezone.utc)
data = [['time', utcnow.strftime('%Y-%m-%d %H:%M:%S')]]

# add modbus data
# product of regs and IDs is set up such that a quantity is retrieved first from
# one meter, then from the other. Hence they a closest in time to minimize
# fluctuations 
try:
  data = data + [[f"{q['quantity']}_{id}", read_modbus(mbclient, id, q)] 
                 for q, id in list(product(regs, IDs))]
except:
    pass

# add temperature data
data = data + [[id, read_temp(thermometers[id])] for id in thermometers]

# retrieve previous data and calculate deltas
cred = read_cred()
prev_row = read_last(cred)
data = data + [
    ['delta_time', (utcnow - prev_row['time']).dt.total_seconds()[0]],
    ['delta_total_energy_1', dict(data)['total_energy_1'] - prev_row['total_energy_1'][0]],
    ['delta_total_energy_2', dict(data)['total_energy_2'] - prev_row['total_energy_2'][0]]]

# cobble together the SQL insert statement and execute it
# need to distinguish between strings and floats for the values
fields = ','.join([x[0] for x in data])
values = ','.join(['%.12f' % x[1] if isinstance(x[1], float) else '"%s"' % x[1] for x in data])
sql = f'insert into data ({fields}) values ({values})'

cur.execute(sql)
conn.commit()


# close connections
mbclient.close()
conn.close()
