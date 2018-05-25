import configparser
import datetime

import requests
from sense_energy import Senseable

# https://pvoutput.org/help.html#api-spec
PV_OUTPUT_STATUS_URL = 'https://pvoutput.org/service/r2/addstatus.jsp'

config = configparser.ConfigParser()

config.read('config.ini')

sense_username = config.get('sense_credentials', 'email')
sense_password = config.get('sense_credentials', 'password')

sense = Senseable(sense_username, sense_password)

print("Active:", sense.active_power, "W")
print("Active Solar:", sense.active_solar_power, "W")
print("Active Devices:", ", ".join(sense.active_devices))
print("Daily Usage:", sense.daily_usage, "kWh")
print("Daily Production:", sense.daily_production, "kWh")

pvoutput_apikey = config.get('pvoutput_credentials', 'api_key')
pvoutput_system_id = config.get('pvoutput_credentials', 'system_id')

datetime = datetime.datetime.now()

date = datetime.strftime('%Y%m%d')
time = datetime.strftime('%H:%M')

pvoutput_request_headers = {
    'X-Pvoutput-Apikey':   pvoutput_apikey,
    'X-Pvoutput-SystemId': pvoutput_system_id,
}

pvoutput_request_data = {
    'd':  date,
    't':  time,
    # 'v1': sense.daily_production * 1000,
    # 'v2': sense.active_solar_power,
    'v3': sense.daily_usage * 1000,
    'v4': sense.active_power,
}

pvoutput_response = requests.post(PV_OUTPUT_STATUS_URL, headers=pvoutput_request_headers,
                                  data=pvoutput_request_data)
