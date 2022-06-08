# Datenerfassung der Heizung

## Daten der Temperatursensoren einlesen

* Knoten rpi-ds18b20 liest alle Sensoren aus
* Daten werden nach ID der Sensoren gesplittet
* Signale werden umbenannt und in Influxdb gespeichert
* Zuordnung bisher:
  * A6547F020800 = Vorlauftemperatur
  * D6AC18040000 = Außentemperatur
  * 18587F020800 = Rücklauftemperatur


## Daten der Stromzähler einlesen

* Kommunikation über RS485-USB-Konverter (funktionierte out of the box) mit
  folgenden Einstellungen: 
  * Modbus-Version: RTU
  * Baudrate: 9600
  * Data Bits: 8
  * Stop Bits: 1
  * Parity: Even
* Kommandozeilen-Tool, um mit Geräten zu kommunizieren ist `modbus`,
  https://github.com/favalex/modbus-cli. Dort auch Beschreibung der
  Access-Query-Syntax. 
  * Kann per `pip3 install modbus_cli` installiert werden
  * Beispiel-Query: `modbus --slave-id 1 --parity e -v --baud 9600 --timeout 2  /dev/ttyUSB0 h@2/H`
    * `--slave-id 1`: Modbus ID
    * `--parity e --baud 9600`: Parity even, Baudrate 9600
    * `--timeout 2`: Timeout, klar
    * `/dev/ttyUSB0`: USB-Gerät
    * `h@2/H`: Eigentlicher Query, hier: Frage ein holding-Register ab, das
      bei Adresse 2 (dezimal) beginnt, und erwarte als Antwort eine 16-bit
      Integer. Die Netzfrequenz beispielsweise wird per `h@20/f` abgefragt
      (Adresse 0x14 = 20, Ergebnis 32-bit Float)
* Zähler haben per Voreinstellung beide die Modbus ID 1. Setzen der ID per 
  `modbus --slave-id 1 --parity e -v --baud 9600 --timeout 2  /dev/ttyUSB0 h@2/h=2`
* Einstellungen der `Modbus-Getter`-Nodes:
  * `Unit-Id`: Modbus-ID
  * `FC`: Was man tun will, i.e., "Read Holding Registers"
  * `Address`: Register-Nummer (siehe Orno-Doku)
  * `Quantity`: Wieviele 16-bit-Zahlen gelesen werden sollen
* In Node Red muss noch dafür gesorgt werden, dass aus den zurückgegebenen Daten
  eine vernünftige Zahl gebaut wird. Dazu wird der `buffer-parser`-Node
  eingesetzt.

## Influxdb

* Einloggen: `influx -username admin -password XXXXXXXXXXXX -precision rfc3339 -database temperatures`

## MariaDB @ DS218j

* Einloggen von remote nur mit remoteuser
* Ein paar Befehle:
  * `create database measurements;`
  * `use measurements;`
  * `
create table data(
  time                timestamp, 
  aussentemperatur    double, 
  vorlauftemperatur   double, 
  ruecklauftemperatur double,
  frequency_1         double,
  l1_voltage_1        double,
  l2_voltage_1        double,
  l3_voltage_1        double,
  l1_current_1        double,
  l2_current_1        double,
  l3_current_1        double,
  total_power_1       double,
  l1_power_1          double,
  l2_power_1          double,
  l3_power_1          double,
  total_energy_1      double,
  l1_energy_1         double,
  l2_energy_1         double,
  l3_energy_1         double,
  frequency_2         double,
  l1_voltage_2        double,
  l2_voltage_2        double,
  l3_voltage_2        double,
  l1_current_2        double,
  l2_current_2        double,
  l3_current_2        double,
  total_power_2       double,
  l1_power_2          double,
  l2_power_2          double,
  l3_power_2          double,
  total_energy_2      double,
  l1_energy_2         double,
  l2_energy_2         double,
  l3_energy_2         double
);
`