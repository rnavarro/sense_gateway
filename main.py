import configparser
import datetime
from datetime import timedelta

import requests

from sense import Sense

config = configparser.ConfigParser()
config.read('config.ini')

datetime = datetime.datetime.now()

####################
# Get Sense Data #
####################

sense_username = config.get('sense_credentials', 'email')
sense_password = config.get('sense_credentials', 'password')

sense = Sense(sense_username, sense_password)

####################
# Get Weather Data #
####################

wunderground_api_key = config.get('wunderground_credentials', 'api_key')
wunderground_station_id = config.get('wunderground_credentials', 'station_id')

wunderground_url = 'http://api.wunderground.com/api/%s/conditions/q/pws:%s.json' \
                   % (wunderground_api_key, wunderground_station_id)

wunderground_response = requests.get(wunderground_url).json()

wunderground_temperature = wunderground_response['current_observation']['temp_c']

######################
# Get SolarEdge Data #
######################

solaredge_api_key = config.get('solaredge_credentials', 'api_key')
solaredge_site_id = config.get('solaredge_credentials', 'site_id')
solaredge_serial_number = config.get('solaredge_credentials', 'serial_number')

solaredge_url = 'https://monitoringapi.solaredge.com/equipment/%s/%s/data' \
                % (solaredge_site_id, solaredge_serial_number)

solaredge_start_time = datetime - timedelta(minutes=5)
solaredge_end_time = datetime + timedelta(minutes=5)

solaredge_request_payload = {
    'startTime': solaredge_start_time.isoformat(' ', timespec='seconds'),
    'endTime':   solaredge_end_time.isoformat(' ', timespec='seconds'),
    'api_key':   solaredge_api_key
}

solaredge_response = requests.get(solaredge_url, params=solaredge_request_payload).json()

solaredge_dc_voltage = solaredge_response['data']['telemetries'][0]['dcVoltage']

################
# Display Data #
################

print("\n" + datetime.isoformat(' '))
print("Active:", sense.active_power, "W")
print("Active Solar:", sense.active_solar_power, "W")
print("Active Devices:", ", ".join(sense.active_devices))
print("Daily Usage:", sense.daily_usage, "kWh")
print("Daily Production:", sense.daily_production, "kWh")
print("Temperature:", wunderground_temperature, "F")
print("DC Voltage:", solaredge_dc_voltage, "V")

pvoutput_apikey = config.get('pvoutput_credentials', 'api_key')
pvoutput_system_id = config.get('pvoutput_credentials', 'system_id')

date = datetime.strftime('%Y%m%d')
time = datetime.strftime('%H:%M')

pvoutput_request_data = {
    'd':  date,
    't':  time,
    'v1': sense.daily_production * 1000,
    'v2': sense.active_solar_power,
    'v3': sense.daily_usage * 1000,
    'v4': sense.active_power,
    'v5': wunderground_temperature,
    'v6': solaredge_dc_voltage,
}

# https://pvoutput.org/help.html#api-spec
pvoutput_response = requests.post('https://pvoutput.org/service/r2/addstatus.jsp',
                                  headers={
                                      'X-Pvoutput-Apikey':   pvoutput_apikey,
                                      'X-Pvoutput-SystemId': pvoutput_system_id,
                                  },
                                  data=pvoutput_request_data)
