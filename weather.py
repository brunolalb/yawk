from dataclasses import dataclass
from datetime import datetime, timedelta
from xml.dom.minidom import parseString
import requests
from requests.exceptions import RequestException
import time
from typing import List


@dataclass
class weather_forecast:
    low: float
    high: float
    condition: str
    # icon's path
    icon: str
    # weekday's name (monday, tuesday, ...)
    day: str

@dataclass
class weather_current:
    city: str
    temperature: float
    humidity: float
    wind: float
    condition: str
    icon: str

class yawkWeather():
    def __init__(self, cfg):
        self.cfg = cfg
        self.city_id = self.cfg['city']
        self.api_key = self.cfg['api']

        # simple test just to see if the city id and api key are working
        params = {'id': self.cfg['city'],
                  'units': 'metric',
                  'mode': 'xml',
                  'APPID': self.cfg['api']}
        try:
            requests.get("http://api.openweathermap.org/data/2.5/weather", params=params)
        except RequestException as e:
            raise ValueError("API failed, check city_id and api_key:\r\n{}".format(e))

    @staticmethod
    def _most_frequent(_list):
        data = {}
        count, itm = 0, ''
        for item in reversed(_list):
            data[item] = data.get(item, 0) + 1
            if data[item] >= count:
                count, itm = data[item], item
        return itm

    def get_weather_forecast(self) -> List[weather_forecast]:
        print("Getting weather forecast information . . .")

        params = {'id': self.cfg['city'],
                  'units': 'metric',
                  'mode': 'xml',
                  'APPID': self.cfg['api']}

        for attempt in range(5):
            try:
                weather_data = requests.get("http://api.openweathermap.org/data/2.5/forecast", params=params).text
                break  # If the requests succeeds break out of the loop
            except RequestException as e:
                print("API call failed {}".format(e))
                time.sleep(2 ** attempt)
                continue  # if not try again. Basically useless since it is the last command but we keep it for clarity
        else:
            # If we could get the data within 5 tries, stop.
            print("Could not retrieve data from API")
            raise ValueError("Could not retrieve data from API")

        dom = parseString(weather_data)
        data = []
        data: List[weather_forecast]

        times = dom.getElementsByTagName('time')

        # get today's date from the xml
        today = datetime.strptime(times[0].getAttribute('from'), '%Y-%m-%dT%H:%M:%S')

        for d in range(5):
            day = today + timedelta(days=d)
            day = day.strftime("%Y-%m-%d")
            forecasts = [t for t in times if day in t.getAttribute('from')]
            min = 10000.0
            max = -10000.0
            day_condition = list()
            icon = list()
            for forecast in forecasts:
                temp = forecast.getElementsByTagName('temperature')[0]
                min1 = float(temp.getAttribute('min'))
                max1 = float(temp.getAttribute('max'))
                if min > min1:
                    min = min1
                if max < max1:
                    max = max1
                day_condition.append(str(forecast.getElementsByTagName('symbol')[0].getAttribute('name')))
                icon.append(str(forecast.getElementsByTagName('symbol')[0].getAttribute('var')))

            data.append(weather_forecast(low=min, 
                                         high=max, 
                                         condition=self._most_frequent(day_condition),
                                         icon="icons/" + self._most_frequent(icon) + ".png", 
                                         day=(today + timedelta(days=d)).strftime("%A")))

        # minor fix for the temperature today...
        if float(data[0].low) > float(self.current_temperature):
            data[0].low = self.current_temperature
        if float(data[0].high) < float(self.current_temperature):
            data[0].high = self.current_temperature

        return data

    def get_weather_current(self) -> weather_current:
        print("Getting current weather information . . .")
        print("Checking the API")

        params = {'id': self.cfg['city'],
                  'units': 'metric',
                  'mode': 'xml',
                  'APPID': self.cfg['api']}

        for attempt in range(5):
            try:
                weather_data = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params).text
                break # If the requests succeeds break out of the loop
            except RequestException as e:
                print("API call failed {}".format(e))
                time.sleep(2**attempt)
                continue # if not try again. Basically useless since it is the last command but we keep it for clarity
        else:
            # If we could get the data within 5 tries, stop.
            print("Could not retrieve data from API")
            raise ValueError("Could not retrieve data from API")

        dom = parseString(weather_data)

        city_name = dom.getElementsByTagName('city')[0].getAttribute('name')
        country_code = dom.getElementsByTagName('country')[0].firstChild.nodeValue
        current_temperature_float = float(dom.getElementsByTagName('temperature')[0].getAttribute('value'))
        current_humidity = float(dom.getElementsByTagName('humidity')[0].getAttribute('value'))
        current_condition = dom.getElementsByTagName('weather')[0].getAttribute('value')
        current_icon = "icons/" + dom.getElementsByTagName('weather')[0].getAttribute('icon') + ".png"
        current_wind = float(dom.getElementsByTagName('speed')[0].getAttribute('value')) * 3.6
        current_wind_desc = dom.getElementsByTagName('speed')[0].getAttribute('name')


        data = weather_current(city=city_name + ", " + country_code,
                               temperature=current_temperature_float,
                               humidity=current_humidity,
                               wind=current_wind,
                               condition=current_condition,
                               icon=current_icon)
        self.current_temperature = data.temperature

        return data
