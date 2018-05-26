import configparser
import datetime
import logging
import time

from sense import Sense


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z'
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

    daily_energy_usage = 0
    power_usage_data = []

    # This is just to make sure we don't shoot out 0 values
    if daily_energy_usage < sense.daily_usage * 1000:
        daily_energy_usage = sense.daily_usage * 1000

    while True:
        dt = datetime.datetime.now()

        # Gather Power Consumption Every 5s
        if dt.second % 5 == 0:
            # Fetch the latest data
            sense.get_realtime()

            print("\n", dt)
            print("Current Power Usage", sense.active_power, "W")
            print("Sense Daily Usage", sense.daily_usage * 1000, "Wh")
            print("Calculated Daily Usage", daily_energy_usage, "Wh")

            power_usage_data.append(sense.active_power)

        # Roll Up Power Consumption Every 60s
        if dt.second % 60 == 0:
            print("\n")
            logging.debug("Roll Up Power Usage")

            power_usage = 0
            for metric in power_usage_data:
                power_usage += metric

            watts_per_second = power_usage / len(power_usage_data)
            kilowatts_per_hour = watts_per_second / 3600 / 1000

            daily_energy_usage += kilowatts_per_hour

            print("Updated Daily Usage", daily_energy_usage, "Wh")

            power_usage_data = []

        # True Up Power Consumption Every 60m
        if dt.minute % 60 == 0:
            print("\n")
            logging.debug("Hourly Power True Up")
            print("Sense Daily Usage", sense.daily_usage * 1000, "Wh")
            print("Calculated Daily Usage", daily_energy_usage, "Wh")

            if sense.daily_usage > daily_energy_usage * 1000:
                daily_energy_usage = sense.daily_usage * 1000

        time.sleep(1)


if __name__ == '__main__':
    main()
