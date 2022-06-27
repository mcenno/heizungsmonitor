import sys
from itertools import product
from struct import pack, unpack
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from time import sleep
from datetime import datetime
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", type=str,
                    help="select quantity")
parser.add_argument("-i", "--id", type=int, choices=[1, 2],
                    help="id of meter to read")
args = parser.parse_args()

# registers we want to read
# see documentation at https://b2b.orno.pl/download-resource/26064/
regs = {
    'frequency'   : {'reg': 0x014, 'size': 2},
    'l1_voltage'  : {'reg': 0x00e, 'size': 2},
    'l2_voltage'  : {'reg': 0x010, 'size': 2},
    'l3_voltage'  : {'reg': 0x012, 'size': 2},
    'l1_current'  : {'reg': 0x016, 'size': 2},
    'l2_current'  : {'reg': 0x018, 'size': 2},
    'l3_current'  : {'reg': 0x01a, 'size': 2},
    'total_power' : {'reg': 0x01c, 'size': 2},
    'l1_power'    : {'reg': 0x01e, 'size': 2},
    'l2_power'    : {'reg': 0x020, 'size': 2},
    'l3_power'    : {'reg': 0x022, 'size': 2},
    'total_energy': {'reg': 0x100, 'size': 2},
    'l1_energy'   : {'reg': 0x102, 'size': 2},
    'l2_energy'   : {'reg': 0x104, 'size': 2},
    'l3_energy'   : {'reg': 0x106, 'size': 2},
}

# definition of temperature sensors
thermometers = {
                'aussentemperatur':    '28-00000418acd6',
                'vorlauftemperatur':   '10-0008027f54a6',
                'ruecklauftemperatur': '10-0008027f5818',
                'warmwassertemperatur': '28-6757b90164ff',
                'zirkulationsruecklauf': '28-1704b20164ff'
                }

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
data = [['time', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')]]

# add modbus data
# connect to Modbus
mbclient = ModbusClient(method='rtu', 
                        port='/dev/ttyUSB0', 
                        baudrate=9600,
                        bytesize=8, 
                        stopbits=1,
                        parity='E',
                        timeout=1)

mbclient.connect()
row = regs[args.name]
data.append([f"{args.name}_{args.id}", read_modbus(mbclient, args.id, row)])
mbclient.close()

for e in data:
    print(e)