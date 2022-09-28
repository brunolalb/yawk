from cgitb import small
import configparser
from dataclasses import dataclass
from operator import ne
from typing import List
import socket
import tempfile
import time
from datetime import datetime
from subprocess import call
from sys import platform
import os
from xml.etree.ElementInclude import include

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from PIL.Image import Image as PilImage
from weather import weather_current, weather_forecast, yawkWeather

try:
    from _fbink import ffi, lib as fbink
except ImportError:
    from fbink_mock import ffi, lib as fbink

CONFIGFILE = "config.ini"


def wait_for_wifi():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_addr = s.getsockname()[0]
            print("Connected, with the IP address: " + ip_addr)
            return ip_addr
        except Exception as e:
            print("exc. ignored {}".format(e))
            os.system("reboot")
        time.sleep(15)


def get_config_data(file_path):
    """turns the config file data into a dictionary"""
    parser = configparser.RawConfigParser()
    parser.read(file_path)
    data = dict()
    data['api_key'] = parser.get("yawk", "key")
    data['city_id'] = parser.get("yawk", "city")

    print("api: {}\ncity: {}".format(data['api_key'], data['city_id']))

    return data

@dataclass
class box_descriptor:
    pos_x: int
    pos_y: int
    width: int
    height: int

@dataclass
class boxes:
    current: box_descriptor
    today: box_descriptor
    tomorrow: box_descriptor
    next_days: List[box_descriptor]


@dataclass
class fonts:
    tiny: FreeTypeFont
    small: FreeTypeFont
    comfort: FreeTypeFont
    big: FreeTypeFont


@dataclass
class icons:
    wind: PilImage
    humidity: PilImage
    temperature: PilImage

@dataclass
class data:
    current: weather_current
    forecast: List[weather_forecast]


class YAWK:
    # BORDER, in pixels, so we don't draw too close to the edges
    BORDER = 10
    def __init__(self):

        # config from the file
        self.cfg_data = dict()
        cfg_file_data = get_config_data(CONFIGFILE)
        self.cfg_data['api'] = cfg_file_data['api_key']
        self.cfg_data['city'] = cfg_file_data['city_id']

        # fbink configuration
        self.fbink_cfg = ffi.new("FBInkConfig *")
        self.fbink_cfg.is_centered = True
        self.fbink_cfg.is_halfway = True
        self.fbink_cfg.is_cleared = True

        self.fbfd = fbink.fbink_open()
        fbink.fbink_init(self.fbfd, self.fbink_cfg)
        state = ffi.new("FBInkState *")
        fbink.fbink_get_state(self.fbink_cfg, state)

        if "linux" in platform:
            self.screen_size = (state.view_width, state.view_height)
        else:
            self.screen_size = (768, 1024)

        # app configuration
        self.ip_address = "1.1.1.1"

        # weather class instance
        try:
            self.weather_fetcher = yawkWeather(self.cfg_data)
            self.weather = data(current=self.weather_fetcher.get_weather_current(),
                                forecast=self.weather_fetcher.get_weather_forecast())
        except Exception as e:
            print(e)
            fbink.fbink_close(self.fbfd)
            
        # configuration for the image
        # Boxes positions
        #   current condition
        current = box_descriptor(0, 0, int(2 * self.screen_size[0] / 3), int(self.screen_size[1] / 3))
        #   today's forecast
        today = box_descriptor(current.width, 0, self.screen_size[0] - current.width, current.height)
        #   tomorrow
        tomorrow = box_descriptor(0, current.height, self.screen_size[0], int((self.screen_size[1] - current.height) / 3))
        #   next 3 days
        next_day0 = box_descriptor(0, current.height + tomorrow.height, int(self.screen_size[0] / 3), self.screen_size[1] - current.height - tomorrow.height)
        next_day1 = box_descriptor(next_day0.width, next_day0.pos_y, next_day0.width, next_day0.height)
        next_day2 = box_descriptor(next_day1.pos_x + next_day1.width, next_day1.pos_y, next_day1.width, next_day1.height)
        self.boxes = boxes(current, today, tomorrow, [next_day0, next_day1, next_day2])
        # fonts
        #   tiny: used on the weather condition for the next days and ip address
        #   small: used on the headers and most stuff on the current conditions
        #   comfort: temperatures (gets scaled according to the box)
        #   big: for the current temperature
        self.fonts = fonts(tiny=ImageFont.truetype("fonts/Cabin-Regular.ttf", 22),
                           small=ImageFont.truetype("fonts/Fabrica.otf", 26),
                           comfort=ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 60),
                           big=ImageFont.truetype("fonts/Comfortaa-Regular.ttf", int(self.screen_size[1] / 10)))

        # icons
        self.icons = icons(wind=Image.open('icons/w.png'),
                           humidity=Image.open('icons/h.png'),
                           temperature=Image.open('icons/C.png'))

    def _create_image(self) -> str:

        today = self.weather.forecast[0]
        tomorrow = self.weather.forecast[1]
        days = self.weather.forecast[2:]

        print("Creating image . . .")

        # 758 x 1024
        WIDTH = int(self.screen_size[0])
        HEIGHT = int(self.screen_size[1])

        white = 255
        black = 0
        gray = 128

        img = Image.new('L', (WIDTH, HEIGHT), color=white)
        draw = ImageDraw.Draw(img, 'L')

        # Dividing lines
        # under today/current
        draw.line([(self.BORDER, self.boxes.current.height), (WIDTH - self.BORDER, self.boxes.current.height)], gray)
        # between today/current
        draw.line([(self.boxes.current.width, self.BORDER), (self.boxes.current.width, self.boxes.current.height - self.BORDER)], gray)
        # under tomorrow
        draw.line([(self.BORDER, self.boxes.next_days[0].pos_y), (WIDTH - self.BORDER, self.boxes.next_days[0].pos_y)], gray)
        # between day 3/4
        draw.line([(self.boxes.next_days[1].pos_x, self.boxes.next_days[1].pos_y + self.BORDER), (self.boxes.next_days[1].pos_x, HEIGHT - self.BORDER)], gray)
        # between day 4/5
        draw.line([(self.boxes.next_days[2].pos_x, self.boxes.next_days[2].pos_y + self.BORDER), (self.boxes.next_days[2].pos_x, HEIGHT - self.BORDER)], gray)

        # Current conditions
        # City Name, Country Code, Day, Time
        header = self.weather.current.city + ", " + datetime.now().strftime("%d.%m.%y, %Hh%M")
        header_w, header_h = draw.textsize(header, font=self.fonts.small)
        draw.text((self.boxes.current.width / 2 - header_w / 2, self.BORDER), header, font=self.fonts.small, fill=black)
        # temperature
        
        temp_w, temp_h = draw.textsize(str(round(self.weather.current.temperature, 1)), font=self.fonts.big)
        draw.text((self.BORDER * 3, 2 * self.boxes.current.height / 7), str(round(self.weather.current.temperature, 1)), font=self.fonts.big, fill=black)
        # celsius
        img.paste(self.icons.temperature.resize((self.icons.temperature.size[0] * 2, self.icons.temperature.size[1] * 2)), (self.BORDER * 3 + temp_w, int(2 * self.boxes.current.height / 7)))
        # condition icon
        condition = Image.open(self.weather.current.icon)
        condition = condition.resize((int(condition.size[0] * 1.2), int(condition.size[1] * 1.2)))
        temp_end_x = self.BORDER * 3 + temp_w + self.icons.temperature.size[0] * 2
        x = int((self.boxes.current.width + temp_end_x) / 2 - condition.size[0] / 2)
        img.paste(condition, (x, int(self.boxes.current.height / 2 - condition.size[1] / 2)))
        # condition description - under the icon?
        condition_w, condition_h = draw.textsize(self.weather.current.condition, font=self.fonts.small)
        x = (self.boxes.current.width + temp_end_x) / 2 - condition_w / 2
        y = self.boxes.current.height / 2 + int(condition.size[1] / 2) + 3 * self.BORDER
        draw.text((x, y), self.weather.current.condition, font=self.fonts.small, fill=gray)
        # wind icon
        y = self.boxes.current.height - self.icons.wind.size[1]
        img.paste(self.icons.wind, (self.BORDER, y))
        # wind value
        wind_w, wind_h = draw.textsize(str(int(round(self.weather.current.wind, 0))) + "km/h", font=self.fonts.small)
        y = y + self.icons.wind.size[1] / 2 - wind_h / 2
        draw.text((self.BORDER + self.icons.wind.size[0] + self.BORDER, y), str(int(round(self.weather.current.wind, 0))) + "km/h", font=self.fonts.small, fill=black)
        # humidity icon
        y = self.boxes.current.height - self.icons.wind.size[1] - self.icons.humidity.size[1]
        x = int(self.BORDER + self.icons.wind.size[0] / 2 - self.icons.humidity.size[0] / 2)
        img.paste(self.icons.humidity, (x, y))
        # humidity value
        humidity_w, humidity_h = draw.textsize(str(int(round(self.weather.current.humidity, 0))) + "%", font=self.fonts.small)
        y = y + self.icons.humidity.size[1] / 2 - humidity_h / 2
        draw.text((self.BORDER + self.icons.wind.size[0] + self.BORDER, y), str(int(round(self.weather.current.humidity, 0))) + "%", font=self.fonts.small, fill=black)

        def print_temp(pos:int, text:str, temp:float, scale:float=1.0):
            # text string
            text_w, text_h = draw.textsize(text, font=self.fonts.small)
            y = pos[1] - text_h
            x = pos[0]
            draw.text((x, y), text, font=self.fonts.small, fill=gray)
            # value
            temp_width, temp_height = draw.textsize(str(round(temp, 1)), font=self.fonts.comfort)
            y = y + text_h - temp_height
            x += text_w
            draw.text((x, y), str(round(temp, 1)), font=self.fonts.comfort, fill=black)
            # celsius
            x += temp_width
            img.paste(self.icons.temperature.resize((int(self.icons.temperature.size[0] * scale), int(self.icons.temperature.size[1] * scale))), (int(x), int(y)))

        # today's forecast
        # low temperature
        position = [self.boxes.today.pos_x + self.BORDER, self.boxes.today.height / 4]
        print_temp(position, "low: ", today.low, 1.3)
        # high temperature
        position = [self.boxes.today.pos_x + self.BORDER, 2 * self.boxes.today.height / 4]
        print_temp(position, "high: ", today.high, 1.3)
        # condition icon
        condition = Image.open(today.icon)
        y = int(3 * self.boxes.today.height / 4 - condition.size[1] / 2)
        x = int(self.boxes.today.pos_x + self.boxes.today.width / 2 - condition.size[0] / 2)
        img.paste(condition, (x, y))

        # tomorrow's forecast
        # tomorrow's text
        draw.text((self.boxes.tomorrow.pos_x + self.BORDER, self.boxes.tomorrow.pos_y + self.BORDER), tomorrow.day, font=self.fonts.small, fill=black)
        # low
        x = int(self.boxes.tomorrow.width / 8)
        y = int(self.boxes.tomorrow.pos_y + 2 * self.boxes.tomorrow.height / 3)
        print_temp((x, y), "low: ", tomorrow.low, 1.5)
        # high
        x = int(2 * self.boxes.tomorrow.width / 3)
        print_temp((x, y), "high: ", tomorrow.high, 1.5)
        # condition icon
        condition = Image.open(tomorrow.icon)
        y -= condition.size[1]
        x = int(self.boxes.tomorrow.width / 2 - condition.size[0] / 2)
        img.paste(condition, (x, y))
        # condition description - under the icon
        condition_w, condition_h = draw.textsize(tomorrow.condition, font=self.fonts.small)
        x = int(self.boxes.tomorrow.width / 2 - condition_w / 2)
        y += condition.size[1] + 2 * self.BORDER
        draw.text((x, y), tomorrow.condition, font=self.fonts.small, fill=gray)

        def print_other_days(dimensions:box_descriptor, data:weather_forecast):
            # day name
            day_w, day_h = draw.textsize(data.day, font=self.fonts.small)
            x = int(dimensions.pos_x + dimensions.width / 2 - day_w / 2)
            y = dimensions.pos_y + self.BORDER
            draw.text((x, y), data.day, font=self.fonts.small, fill=black)
            # low temp
            x = dimensions.pos_x + self.BORDER
            y = int(dimensions.pos_y + dimensions.height / 4)
            print_temp((x, y), "low: ", data.low)
            # high temp
            y += int(dimensions.height / 4)
            print_temp((x, y), "high: ", data.high)
            # condition icon
            condition = Image.open(data.icon)
            y += 2 * self.BORDER
            x = int(dimensions.pos_x + dimensions.width / 2 - condition.size[0] / 2)
            img.paste(condition, (x, y))
            # condition description
            condition_w, condition_h = draw.textsize(data.condition, font=self.fonts.tiny)
            y += condition.size[1] + self.BORDER
            x = int(dimensions.pos_x + dimensions.width / 2 - condition_w / 2)
            draw.text((x, y), data.condition, font=self.fonts.tiny, fill=gray)

        # the next 3 days
        for i in range(3):
            print_other_days(self.boxes.next_days[i], days[i])

        # ip address
        ip_w, ip_h = draw.textsize(self.ip_address, font=self.fonts.tiny)
        draw.text((WIDTH - self.BORDER - ip_w, HEIGHT - self.BORDER - ip_h), self.ip_address, font=self.fonts.tiny, fill=gray)

        # battery level
        if "linux" in platform:
            bat_percent = 0
            with open("/sys/class/power_supply/mc13892_bat/capacity") as file:
                bat_percent = file.readline()
                bat_percent = bat_percent.rstrip('\n')
            bat_w, bat_h = draw.textsize(bat_percent + "%", font=self.fonts.tiny)
            draw.text((self.BORDER, HEIGHT - self.BORDER - bat_h), bat_percent + "%", font=self.fonts.tiny, fill=gray)

        if "linux" in platform:
            img.save(tempfile.gettempdir() + "/img.bmp")
            return bytes(tempfile.gettempdir() + "/img.bmp", 'utf-8')
        else:
            img.save(tempfile.gettempdir() + "\\img.bmp")
            return bytes(tempfile.gettempdir() + "\\img.bmp", 'utf-8')

    def update(self):
        try:
            self.weather.current = self.weather_fetcher.get_weather_current()
            self.weather.forecast = self.weather_fetcher.get_weather_forecast()
        except Exception as e:
            # Something went wrong while getting API Data, try again later.
            print("Failed to get weather data:\r\n" + str(e))
            return
        image = self._create_image()
        print("Drawing image")
        rect = ffi.new("FBInkRect *")
        rect.top = 0
        rect.left = 0
        rect.width = 0
        rect.height = 0
        if "linux" in platform:
            fbink_version = ffi.string(fbink.fbink_version()).decode("ascii")
            fbink_version:str
            fbink_version = fbink_version.split(' ')[0]
            fbink_version = fbink_version.split('v')[1]
            major = fbink_version.split('.')[0]
            minor = fbink_version.split('.')[1]
            fbink_version = int(major)*100 + int(minor)
            if fbink_version >= 124:
                fbink.fbink_cls(self.fbfd, self.fbink_cfg, rect, 0)
            else:
                fbink.fbink_cls(self.fbfd, self.fbink_cfg, rect)

        fbink.fbink_print_image(self.fbfd, image, 0, 0, self.fbink_cfg)


def main():
    print("YAWK started!")

    if "linux" in platform:
        call(["hostname", "kobo"])

    wait_for_wifi()

    if "linux" in platform:
        call(["killall", "-TERM", "nickel", "hindenburg", "sickel", "fickel"])

    yawk = YAWK()
    counter = 0

    try:
        while True:
            print("*** Updating at " + datetime.now().strftime("%d.%m.%y, %Hh%M") + " (update nr. " + str(counter) + ") ***")
            yawk.ip_address = wait_for_wifi()
            yawk.update()
            print("Sleeping")
            # sleep 5 min, but ping every 30 seconds... maybe the wifi will stay on
            for sleep in range(10):
                time.sleep(30)
                os.system("ping -c 1 -q www.google.com > /dev/null")
            counter += 1
    finally:
        fbink.fbink_close(yawk.fbfd)


if __name__ == "__main__":
    main()
