import urllib2
from datetime import datetime, timedelta
from xml.dom.minidom import parseString


class yawkWeather():
    def __init__(self, cfg):
        self.cfg = cfg
        if self.cfg['xml_file'] is not None:
            self.read_file = self.cfg['xml_file']
        else:
            self.read_file = None
        if self.cfg['save_data'] is not None:
            self.save_file = self.cfg['save_data']
        else:
            self.save_file = None
        self.city_id = self.cfg['city']
        self.api_key = self.cfg['api']
        # simple test just to see if the city id and api key are working
        weather_link = "http://api.openweathermap.org/data/2.5/forecast?id=" + \
                       self.city_id + \
                       "&units=metric&mode=xml&APPID=" + \
                       self.api_key
        try:
            urllib2.urlopen(weather_link)
        except Exception as e:
            raise ValueError("API failed, check city_id and api_key:\r\n{}".format(e))

    @staticmethod
    def _most_frequent(List):
        data = {}
        count, itm = 0, ''
        for item in reversed(List):
            data[item] = data.get(item, 0) + 1
            if data[item] >= count:
                count, itm = data[item], item
        return itm

    def get_weather_forecast(self):
        print("Getting weather forecast information . . .")

        if self.read_file is False:
            print("Checking the API")
            weather_link = "http://api.openweathermap.org/data/2.5/forecast?id=" + \
                           self.city_id + \
                           "&units=metric&mode=xml&APPID=" + \
                           self.api_key
            try:
                weather_xml = urllib2.urlopen(weather_link)
            except Exception as e:
                print("API failed {}".format(e))
                return None
            weather_data = weather_xml.read()
            weather_xml.close()

            if self.cfg['save_data'] is True:
                print("Saving data")
                file = open('weather.xml', 'w')
                if file is not None:
                    file.write(weather_data)
                    file.close()
                else:
                    print("file not opened")
                    return None
        else:
            print("Checking the file")
            file = open('weather.xml')
            weather_data = file.read()
            file.close()

        dom = parseString(weather_data)

        data = []

        times = dom.getElementsByTagName('time')

        # get today's date from the xml
        today = datetime.strptime(times[0].getAttribute('from'), '%Y-%m-%dT%H:%M:%S')

        for d in range(5):
            day = today + timedelta(days=d)
            day = day.strftime("%Y-%m-%d")
            forecasts = [t for t in times if day in t.getAttribute('from')]
            min = 10000.0
            max = -10000.0
            # print("initial {} {}".format(min, max))
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
            # print("{}: {} to {}, {}".format(day, min, max, _most_frequent(day_condition)))
            data.append({'low': str(round(min, 1)),
                         'high': str(round(max, 1)),
                         'condition': self._most_frequent(day_condition),
                         'icon': "icons/" + self._most_frequent(icon) + ".png",
                         'day': (today + timedelta(days=d)).strftime("%A")
                         })

        # minor fix for the temperature today...
        if float(data[0]['low']) > float(self.current_temperature):
            data[0]['low'] = self.current_temperature
        if float(data[0]['high']) < float(self.current_temperature):
            data[0]['high'] = self.current_temperature

        return data

    def get_weather_current(self):

        print("Getting current weather information . . .")

        if self.cfg['xml_file'] is False:
            print("Checking the API")
            weather_link = "http://api.openweathermap.org/data/2.5/weather?id=" + \
                           self.cfg['city'] + \
                           "&units=metric&mode=xml&APPID=" + \
                           self.cfg['api']
            try:
                weather_xml = urllib2.urlopen(weather_link)
            except Exception as e:
                print("API failed {}".format(e))
                return None
            weather_data = weather_xml.read()
            weather_xml.close()

            if self.cfg['save_data'] is True:
                print("Saving data to file")
                file = open('weather_curr.xml', 'w')
                if file is not None:
                    file.write(weather_data)
                    file.close()
                else:
                    print("file not opened")
                    return None
        else:
            print("Checking the file")
            file = open('weather_curr.xml')
            weather_data = file.read()
            file.close()

        dom = parseString(weather_data)

        city_name = dom.getElementsByTagName('city')[0].getAttribute('name')
        country_code = dom.getElementsByTagName('country')[0].firstChild.nodeValue
        current_temperature_float = float(dom.getElementsByTagName('temperature')[0].getAttribute('value'))
        current_humidity = dom.getElementsByTagName('humidity')[0].getAttribute('value')
        current_condition = dom.getElementsByTagName('weather')[0].getAttribute('value')
        current_icon = "icons/" + dom.getElementsByTagName('weather')[0].getAttribute('icon') + ".png"
        # current_icon = "icons/" + "10n" + ".png"
        current_wind = float(dom.getElementsByTagName('speed')[0].getAttribute('value')) * 3.6
        current_wind_desc = dom.getElementsByTagName('speed')[0].getAttribute('name')

        data = {'city': city_name + ", " + country_code,
                'temperature': str(round(current_temperature_float, 1)),
                'humidity': current_humidity + "%",
                'wind_val': str(int(round(current_wind, 0))) + "km/h",
                'wind_desc': current_wind_desc,
                'condition': current_condition,
                'icon': current_icon}
        self.current_temperature = data['temperature']
        return data
