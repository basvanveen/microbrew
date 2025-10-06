import ujson as json
import time
import machine
import bluetooth
from struct import unpack

validTemperatureModes = ['target', 'manual']
validThermalStates = ["HEATING","COOLING","OFF"]
validtemperatureUnits = ['celsius','fahrenheit']
validStates     = ['on','off']

class MicroBrewery:

    def __init__(self, name, debugmode):
        self.debugmode = debugmode
        self.currentTemperature = None # default
        self.batteryPercentage = None
        self.xAxis = 0
        self.yAxis = 0
        self.zAxis = 0
        self.rssi = None
        self.currentGravity = None
        print(f"Instantiating MicroBrewery: {name}")
        with open('settings/profile.json', 'r') as f:
            self.controlProfile = json.load(f)
            print(json.dumps(self.controlProfile))
        if not self.debugmode:
            self.ble = bluetooth.BLE()
            print("enabling bluetooth")
            print(self.ble.active(True))
            self.doBluetoothScan()

    def update_temperature(self):
        if self.currentTemperature is None:
             return "None received"
        if self.currentTemperature < self.controlProfile['targetTemperature'] - self.controlProfile['hysteresis']:
            self.controlProfile['thermalState'] = "HEATING"
            machine.Pin(self.controlProfile['coolingPin'], machine.Pin.OUT).value(1)
            machine.Pin(self.controlProfile['heatingPin'], machine.Pin.OUT).value(0)
        elif self.currentTemperature > self.controlProfile['targetTemperature'] + self.controlProfile['hysteresis']:
            self.controlProfile['thermalState'] = "COOLING"
            machine.Pin(self.controlProfile['heatingPin'], machine.Pin.OUT).value(1)
            machine.Pin(self.controlProfile['coolingPin'], machine.Pin.OUT).value(0)
        else:
            self.controlProfile['thermalState'] = "OFF"  # Keeps the system stable within range
            machine.Pin(self.controlProfile['heatingPin'], machine.Pin.OUT).value(1)
            machine.Pin(self.controlProfile['coolingPin'], machine.Pin.OUT).value(1)

        return self.controlProfile['thermalState']

    def doBluetoothScan(self):
          """ Point to handler and start
              bluetooth GAP scan loop
          """
          self.ble.irq(self.raptHandler)
          self.ble.gap_scan(0, 3000, 3000)

    def getControlProfile(self):
        return self.controlProfile

    def getTemperature(self):
        if self.debugmode:
              return 123456 # running in debug just output a value 
        return self.currentTemperature
    
    def raptHandler(self, event, data):
        """ IRQ Handler fetching Bluetooth very simple
            approach where we check if advertised data
            contains RAPT string which is enough to unpack
            and parse the data. See rapt repo for more details:
            https://gitlab.com/rapt.io/public/-/wikis/Pill-Hydrometer-Bluetooth-Transmissions
        """
        _, _, _, rssi, adv_data = data # fetch data and received signal strength ignore the rest
        if "RAPT" in bytearray(adv_data):
            try:
                pilldata = unpack(">BfHfhhhH",bytearray(adv_data)[11:])
                if(self.controlProfile['temperatureUnit'] == "celsius"):
                    # Kelvin to Celsius
                    self.currentTemperature    = (pilldata[2] / 128) - 273.15
                else:
                    # Kelvin Fahrenheit
                    self.currentTemperature    = ((pilldata[2] / 128) - 273.15) * 9/5 +32
                self.batteryPercentage     = pilldata[7] / 256
                self.zAxis                 = pilldata[6] / 16
                self.yAxis                 = pilldata[5] / 16
                self.xAxis                 = pilldata[4] / 16
                self.currentGravity        = round(pilldata[3]/1000,5)
                self.rssi                  = rssi
            except ValueError as e:
                # Quick "fix", we sometimes get "buffer too small" we can ignore this
                print(f"Error unpacking data: {e}")

    def getTime(self):
        return f"{(time.localtime()[3]+self.offset)%24:02d}:{time.localtime()[4]:02d}"
    
    def getMetrics(self):
          metrics = self.controlProfile.copy()
          metrics['currentTemperature']      = self.currentTemperature
          metrics['batteryPercentage']      = self.batteryPercentage
          metrics['xAxis']      = self.xAxis
          metrics['yAxis']      = self.yAxis
          metrics['zAxis']      = self.zAxis
          metrics['currentGravity']      = self.currentGravity
          metrics['ReceivedSignalStrength']      = self.rssi
          
          return metrics

    def json_to_prometheus(self, metrics):
        prometheus_output = []
    
        def camel_to_snake(name):
            result = []
            for char in name:
                if char.isupper():
                    result.append('_')
                    result.append(char.lower())
                else:
                    result.append(char)
            return ''.join(result).lstrip('_')
    
        # Mapping string values to numerical representations
        state_mapping = {
            "OFF": 0,
            "HEATING": 1,
            "COOLING": 2
        }
    
        for key, value in metrics.items():
            prometheus_key = camel_to_snake(key)
    
            if key == "thermalState" and value in state_mapping:
                prometheus_output.append(f"{prometheus_key} {state_mapping[value]}")  # Convert string to mapped number
            else:
                prometheus_output.append(f"{prometheus_key} {value}")
    
        return "\n".join(prometheus_output)

    def setControlValue(self,name, value):
        """ set parameters for controller I/O
            lots of if statements due to lack of 
            schema validation or using enum or even
            case switch in micropython atm...
        """
        print(f"name: {name} value: {value}")
        if   name   == 'temperatureMode':
                if value in validTemperatureModes:
                    self.controlProfile['temperatureMode'] = value
        elif name   == 'coolingPin':
                self.controlProfile['coolingPin'] = int(value)
        elif name   == 'heatingPin':
                self.controlProfile['heatingPin'] = int(value)
        elif name   == 'temperatureUnit':
                if value in validtemperatureUnits:
                    self.controlProfile['temperatureUnit'] = value
        elif name   == 'hysteresis':
                self.controlProfile['hysteresis'] = float(value)
        elif name   == 'targetTemperature':
                self.controlProfile['targetTemperature'] = float(value)
        elif name   == 'temperatureSensor':
                self.controlProfile['temperatureSensor'] = value
        else:
            return f"{{'message': '{name} unknown parameter'"
        return self.controlProfile