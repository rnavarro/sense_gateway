import configparser
import datetime
import logging
from datetime import timedelta
from time import sleep

import requests
from websocket import WebSocketTimeoutException

from sense import Sense


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(message)s',
    )

    config = configparser.ConfigParser()
    config.read('config.ini')

    ####################
    # Get Sense Data #
    ####################

    sense_username = config.get('sense_credentials', 'email')
    sense_password = config.get('sense_credentials', 'password')

    sense = Sense(sense_username, sense_password)

    logging.info("Starting Run")

    daily_wh_consumption = 0
    power_consumption_data = []

    daily_wh_production = 0
    power_production_data = []

    with open('power_checkpoint.txt') as f:
        data = f.read().strip().split(',')

        if len(data) > 1:
            checkpoint_date = datetime.datetime.fromtimestamp(float(data[0]))
            daily_wh_production = float(data[1])
            daily_wh_consumption = float(data[2])

            # This happens if we've rolled to the next day but we still have a checkpoint
            # from the day before. We should reset the counters to 0
            if checkpoint_date.day != datetime.datetime.now().day:
                daily_wh_consumption = 0
                daily_wh_production = 0

    # This is just to make sure we don't shoot out 0 values
    sense_daily_wh_consumption = sense.daily_usage * 1000
    sense_daily_wh_production = sense.daily_production * 1000

    if daily_wh_consumption < sense_daily_wh_consumption:
        daily_wh_consumption = sense_daily_wh_consumption

    if daily_wh_production < sense_daily_wh_production:
        daily_wh_production = sense_daily_wh_production

    while True:
        dt = datetime.datetime.now()

        # Fetch the latest data
        try:
            sense.get_realtime()
        except WebSocketTimeoutException:
            logging.warning('Reconnecting Web Socket')
            sense.start_realtime()
            sense.get_realtime()

        # Gather Power Consumption Every 5s
        if dt.second % 5 == 0 and dt.microsecond < 500000:
            current_power_consumption = sense.active_power
            current_power_production = sense.active_solar_power

            if current_power_production < 0:
                current_power_production = 0

            power_consumption_data.append(current_power_consumption)
            power_production_data.append(current_power_production)

            logging.debug("Current Power Consumption: %s W" % current_power_consumption)
            logging.debug("Current Power Production: %s W" % current_power_production)
            logging.debug("")

        # Roll Up Power Metrics Every 60s
        if dt.second % 60 == 0 and dt.microsecond < 500000:
            logging.debug("Roll Up Power Usage")

            power_consumption = 0
            for metric in power_consumption_data:
                power_consumption += metric

            watts_per_second_consumed = power_consumption / len(power_consumption_data)
            watts_per_hour_consumed = watts_per_second_consumed / 3600

            logging.debug("Watts per second (consumption): %s" % watts_per_second_consumed)
            logging.debug("Watts per hour (consumption): %s" % watts_per_hour_consumed)

            daily_wh_consumption += watts_per_hour_consumed

            power_production = 0
            for metric in power_production_data:
                power_production += metric

            watts_per_second_produced = power_production / len(power_production_data)
            watts_per_hour_produced = watts_per_second_produced / 3600

            logging.debug("Watts per second (production): %s" % watts_per_second_produced)
            logging.debug("Watts per hour (production): %s" % watts_per_hour_produced)

            daily_wh_production += watts_per_hour_produced

            logging.debug("")
            logging.debug("Calculated Daily Consumption: %s Wh" % daily_wh_consumption)
            logging.debug("Calculated Daily Production: %s Wh" % daily_wh_production)
            logging.debug("")

            power_consumption_data = []
            power_production_data = []

        # Reset at midnight
        if dt.hour == 0 and dt.minute == 0 and dt.microsecond < 500000:
            a = 1
            daily_wh_consumption = 0
            daily_wh_production = 0

        # True Up Power Metrics Every 5m
        if dt.minute % 5 == 0 and dt.second == 0 and dt.microsecond < 500000:
            sense.update_trend_data()

            sense_daily_wh_consumption = sense.daily_usage * 1000
            sense_daily_wh_production = sense.daily_production * 1000

            logging.debug("Hourly Power True Up")
            logging.debug("Sense Daily Consumption: %s Wh" % sense_daily_wh_consumption)
            logging.debug("Calculated Daily Consumption: %s Wh" % daily_wh_consumption)
            logging.debug("Sense Daily Production: %s Wh" % sense_daily_wh_production)
            logging.debug("Calculated Daily Production: %s Wh" % daily_wh_production)

            if sense_daily_wh_consumption > daily_wh_consumption:
                logging.warning("Resetting daily energy consumption. Sense: %s vs Calculated: %s (Difference: %s)"
                                % (sense_daily_wh_consumption, daily_wh_consumption,
                                   (sense_daily_wh_consumption - daily_wh_consumption)))

                daily_wh_consumption = sense_daily_wh_consumption

            if sense_daily_wh_production > daily_wh_production:
                logging.warning("Resetting daily energy production. Sense: %s vs Calculated: %s (Difference: %s)"
                                % (sense_daily_wh_production, daily_wh_production,
                                   (sense_daily_wh_production - daily_wh_production)))

                daily_wh_production = sense_daily_wh_production

            fh = open('power_checkpoint.txt', 'w+')
            fh.write("%s,%s,%s\n" % (dt.timestamp(), daily_wh_production, daily_wh_consumption))
            fh.close()

            logging.debug("")

        if dt.minute % 5 == 0 and dt.second == 0 and dt.microsecond < 500000:
            logging.debug("Pushing Data to PVOutput")

            wunderground_data = get_wunderground_data(config)

            solaredge_data = {}
            if int(wunderground_data['solar_radiation']) == 0:
                solaredge_data['dc_voltage'] = 0
            else:
                solaredge_data = get_solaredge_data(config, dt)

            ################
            # Display Data #
            ################

            logging.info("Current Power Consumption: %s W" % current_power_consumption)
            logging.info("Current Power Production: %s W" % current_power_production)
            logging.info("Calculated Daily Consumption: %s Wh" % daily_wh_consumption)
            logging.info("Calculated Daily Production: %s Wh" % daily_wh_production)
            logging.info("Temperature: %s C" % wunderground_data['temperature_c'])
            logging.info("Temperature: %s F" % wunderground_data['temperature_f'])
            logging.info("DC Voltage: %s V" % solaredge_data['dc_voltage'])
            logging.info("Solar Radiation: %s w/m^s" % wunderground_data['solar_radiation'])
            logging.debug("")

            pvoutput_apikey = config.get('pvoutput_credentials', 'api_key')
            pvoutput_system_id = config.get('pvoutput_credentials', 'system_id')

            pvoutput_request_data = {
                'd':   dt.strftime('%Y%m%d'),
                't':   dt.strftime('%H:%M'),
                'v1':  daily_wh_production,
                'v2':  current_power_production,
                'v3':  daily_wh_consumption,
                'v4':  current_power_consumption,
                'v5':  wunderground_data['temperature_c'],
                'v6':  solaredge_data['dc_voltage'],
                'v12': wunderground_data['solar_radiation'],
            }

            # https://pvoutput.org/help.html#api-spec
            requests.post('https://pvoutput.org/service/r2/addstatus.jsp',
                          headers={
                              'X-Pvoutput-Apikey':   pvoutput_apikey,
                              'X-Pvoutput-SystemId': pvoutput_system_id,
                          },
                          data=pvoutput_request_data)

            logging.debug("")

        sleep(0.5)


def get_wunderground_data(config):
    ####################
    # Get Weather Data #
    ####################

    wunderground_api_key = config.get('wunderground_credentials', 'api_key')
    wunderground_station_id = config.get('wunderground_credentials', 'station_id')

    wunderground_url = 'http://api.wunderground.com/api/%s/conditions/q/pws:%s.json' \
                       % (wunderground_api_key, wunderground_station_id)

    wunderground_response = requests.get(wunderground_url).json()

    return {
        'temperature_c':   wunderground_response['current_observation']['temp_c'],
        'temperature_f':   wunderground_response['current_observation']['temp_f'],
        'solar_radiation': wunderground_response['current_observation']['solarradiation'],
    }


def get_solaredge_data(config, dt):
    ######################
    # Get SolarEdge Data #
    ######################

    solaredge_api_key = config.get('solaredge_credentials', 'api_key')
    solaredge_site_id = config.get('solaredge_credentials', 'site_id')
    solaredge_serial_number = config.get('solaredge_credentials', 'serial_number')

    solaredge_url = 'https://monitoringapi.solaredge.com/equipment/%s/%s/data' \
                    % (solaredge_site_id, solaredge_serial_number)

    solaredge_start_time = dt - timedelta(minutes=10)
    solaredge_end_time = dt

    solaredge_request_payload = {
        'startTime': solaredge_start_time.isoformat(' ', timespec='seconds'),
        'endTime':   solaredge_end_time.isoformat(' ', timespec='seconds'),
        'api_key':   solaredge_api_key
    }

    solaredge_response = requests.get(solaredge_url, params=solaredge_request_payload).json()

    index = solaredge_response['data']['count'] - 1

    return {
        'dc_voltage': solaredge_response['data']['telemetries'][index]['dcVoltage']
    }


if __name__ == '__main__':
    main()
