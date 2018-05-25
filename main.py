import configparser
import datetime

import requests
from sense_energy import Senseable

# https://pvoutput.org/help.html#api-spec
PV_OUTPUT_STATUS_URL = 'https://pvoutput.org/service/r2/addstatus.jsp'

API_URL = 'https://api.sense.com/apiservice/api/v1/'
API_TIMEOUT = 1

config = configparser.ConfigParser()
config.read('config.ini')

datetime = datetime.datetime.now()

sense_username = config.get('sense_credentials', 'email')
sense_password = config.get('sense_credentials', 'password')

sense = Senseable(sense_username, sense_password)


def get_daily_usage():
    response = sense.s.get(API_URL + 'app/history/trends?monitor_id=%s&scale=DAY&start=%s' %
                           (sense.sense_monitor_id, datetime.utcnow().isoformat()[:-3] + 'Z'),
                           headers=sense.headers, timeout=API_TIMEOUT)
    data = response.json()

    return data


daily_usage = get_daily_usage()

print(datetime.isoformat(' '))
print("Active:", sense.active_power, "W")
print("Active Solar:", sense.active_solar_power, "W")
print("Active Devices:", ", ".join(sense.active_devices))
print("Daily Usage:", daily_usage['consumption']['total'], "kWh")
print("Daily Production:", daily_usage['production']['total'], "kWh")

pvoutput_apikey = config.get('pvoutput_credentials', 'api_key')
pvoutput_system_id = config.get('pvoutput_credentials', 'system_id')

date = datetime.strftime('%Y%m%d')
time = datetime.strftime('%H:%M')

pvoutput_request_headers = {
    'X-Pvoutput-Apikey':   pvoutput_apikey,
    'X-Pvoutput-SystemId': pvoutput_system_id,
}

pvoutput_request_data = {
    'd':  date,
    't':  time,
    # 'v1': daily_usage['production']['total'] * 1000,
    # 'v2': sense.active_solar_power,
    'v3': daily_usage['consumption']['total'] * 1000,
    'v4': sense.active_power,
}

pvoutput_response = requests.post(PV_OUTPUT_STATUS_URL, headers=pvoutput_request_headers,
                                  data=pvoutput_request_data)
