import configparser
import socket
import tempfile
import time
from datetime import datetime
from subprocess import call
from sys import platform

from PIL import Image, ImageDraw, ImageFont
from weather import yawkWeather

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


class YAWK:
    # BORDER, in pixels, so we don't draw to close to the edges
    BORDER = 10
    def __init__(self):
        self.cfg_data = dict()
        cfg_file_data = get_config_data(CONFIGFILE)
        self.cfg_data['api'] = cfg_file_data['api_key']
        self.cfg_data['city'] = cfg_file_data['city_id']

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
        self.forecast = None
        self.current = None
        self.ip_address = "1.1.1.1"

        try:
            self.weather = yawkWeather(self.cfg_data)
        except ValueError as e:
            print(e)
            fbink.fbink_close(self.fbfd)
            
        # configuration for the image
        # Boxes positions
        #   current condition
        self.box_CURRENT = {'x': 0, 'y': 0, 'w': int(2 * self.screen_size[0] / 3), 'h': int(self.screen_size[1] / 3)}
        #   today's forecast
        self.box_TODAY = {'x': self.box_CURRENT['w'], 'y': 0, 'w': self.screen_size[0] - self.box_CURRENT['w'], 'h': self.box_CURRENT['h']}
        #   tomorrow
        self.box_TOMORROW = {'x': 0, 'y': self.box_CURRENT['h'], 'w': self.screen_size[0], 'h': int((self.screen_size[1] - self.box_CURRENT['h']) / 3)}
        #   next 3 days
        self.boxes_NEXT_DAYS = [{'x': 0, 'y': self.box_CURRENT['h'] + self.box_TOMORROW['h'], 'w': int(self.screen_size[0] / 3), 'h': self.screen_size[1] - self.box_CURRENT['h'] - self.box_TOMORROW['h']}]
        self.boxes_NEXT_DAYS.append({'x': self.boxes_NEXT_DAYS[0]['w'], 'y': self.boxes_NEXT_DAYS[0]['y'], 'w': self.boxes_NEXT_DAYS[0]['w'], 'h': self.boxes_NEXT_DAYS[0]['h']})
        self.boxes_NEXT_DAYS.append({'x': self.boxes_NEXT_DAYS[1]['x'] + self.boxes_NEXT_DAYS[1]['w'], 'y': self.boxes_NEXT_DAYS[1]['y'], 'w': self.boxes_NEXT_DAYS[1]['w'], 'h': self.boxes_NEXT_DAYS[1]['h']})
        # fonts
        #   used on the weather condition for the next days and ip address
        self.font_tiny = ImageFont.truetype("fonts/Cabin-Regular.ttf", 22)
        #   used on the headers and most stuff on the current conditions
        self.font_small = ImageFont.truetype("fonts/Fabrica.otf", 26)
        #   temperatures (gets scaled according to the box)
        self.font_comfortaa = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 60)
        #   for the current temperature
        self.font_main_temperature = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", int(self.screen_size[1] / 10))        
        # icons
        self.icon_celsius = Image.open('icons/C.png')
        self.icon_wind = Image.open('icons/w.png')
        self.icon_humidity = Image.open('icons/h.png')

    def _create_image(self):

        if self.forecast is not None and len(self.forecast) != 0:
            today = self.forecast[0]
            tomorrow = self.forecast[1]
            days = self.forecast[2:]
        else:
            return ""

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
        draw.line([(self.BORDER, self.box_CURRENT['h']), (WIDTH - self.BORDER, self.box_CURRENT['h'])], gray)
        # between today/current
        draw.line([(self.box_CURRENT['w'], self.BORDER), (self.box_CURRENT['w'], self.box_CURRENT['h'] - self.BORDER)], gray)
        # under tomorrow
        draw.line([(self.BORDER, self.boxes_NEXT_DAYS[0]['y']), (WIDTH - self.BORDER, self.boxes_NEXT_DAYS[0]['y'])], gray)
        # between day 3/4
        draw.line([(self.boxes_NEXT_DAYS[1]['x'], self.boxes_NEXT_DAYS[1]['y'] + self.BORDER), (self.boxes_NEXT_DAYS[1]['x'], HEIGHT - self.BORDER)], gray)
        # between day 4/5
        draw.line([(self.boxes_NEXT_DAYS[2]['x'], self.boxes_NEXT_DAYS[2]['y'] + self.BORDER), (self.boxes_NEXT_DAYS[2]['x'], HEIGHT - self.BORDER)], gray)

        # Current conditions
        # City Name, Country Code, Day, Time
        header = self.current['city'] + ", " + datetime.now().strftime("%d.%m.%y, %Hh%M")
        header_w, header_h = draw.textsize(header, font=self.font_small)
        draw.text((self.box_CURRENT['w'] / 2 - header_w / 2, self.BORDER), header, font=self.font_small, fill=black)
        # temperature
        
        temp_w, temp_h = draw.textsize(self.current['temperature'], font=self.font_main_temperature)
        draw.text((self.BORDER * 3, 2 * self.box_CURRENT['h'] / 7), self.current['temperature'], font=self.font_main_temperature, fill=black)
        # celsius
        img.paste(self.icon_celsius.resize((self.icon_celsius.size[0] * 2, self.icon_celsius.size[1] * 2)), (self.BORDER * 3 + temp_w, int(2 * self.box_CURRENT['h'] / 7)))
        # condition icon
        condition = Image.open(self.current['icon'])
        condition = condition.resize((int(condition.size[0] * 1.2), int(condition.size[1] * 1.2)))
        temp_end_x = self.BORDER * 3 + temp_w + self.icon_celsius.size[0] * 2
        x = int((self.box_CURRENT['w'] + temp_end_x) / 2 - condition.size[0] / 2)
        img.paste(condition, (x, int(self.box_CURRENT['h'] / 2 - condition.size[1] / 2)))
        # condition description - under the icon?
        condition_w, condition_h = draw.textsize(self.current['condition'], font=self.font_small)
        x = (self.box_CURRENT['w'] + temp_end_x) / 2 - condition_w / 2
        y = self.box_CURRENT['h'] / 2 + int(condition.size[1] / 2) + 3 * self.BORDER
        draw.text((x, y), self.current['condition'], font=self.font_small, fill=gray)
        # wind icon
        y = self.box_CURRENT['h'] - self.icon_wind.size[1]
        img.paste(self.icon_wind, (self.BORDER, y))
        # wind value
        wind_w, wind_h = draw.textsize(self.current['wind_val'], font=self.font_small)
        y = y + self.icon_wind.size[1] / 2 - wind_h / 2
        draw.text((self.BORDER + self.icon_wind.size[0] + self.BORDER, y), self.current['wind_val'], font=self.font_small, fill=black)
        # humidity icon
        y = self.box_CURRENT['h'] - self.icon_wind.size[1] - self.icon_humidity.size[1]
        x = int(self.BORDER + self.icon_wind.size[0] / 2 - self.icon_humidity.size[0] / 2)
        img.paste(self.icon_humidity, (x, y))
        # humidity value
        humidity_w, humidity_h = draw.textsize(self.current['humidity'], font=self.font_small)
        y = y + self.icon_humidity.size[1] / 2 - humidity_h / 2
        draw.text((self.BORDER + self.icon_wind.size[0] + self.BORDER, y), self.current['humidity'], font=self.font_small, fill=black)

        def print_temp(pos, text, temp, scale=1.0):
            # text string
            text_w, text_h = draw.textsize(text, font=self.font_small)
            y = pos[1] - text_h
            x = pos[0]
            draw.text((x, y), text, font=self.font_small, fill=gray)
            # value
            temp_width, temp_height = draw.textsize(temp, font=self.font_comfortaa)
            y = y + text_h - temp_height
            x += text_w
            draw.text((x, y), temp, font=self.font_comfortaa, fill=black)
            # celsius
            x += temp_width
            img.paste(self.icon_celsius.resize((int(self.icon_celsius.size[0] * scale), int(self.icon_celsius.size[1] * scale))), (int(x), int(y)))

        # today's forecast
        # low temperature
        position = [self.box_TODAY['x'] + self.BORDER, self.box_TODAY['h'] / 4]
        print_temp(position, "low: ", today['low'], 1.3)
        # high temperature
        position = [self.box_TODAY['x'] + self.BORDER, 2 * self.box_TODAY['h'] / 4]
        print_temp(position, "high: ", today['high'], 1.3)
        # condition icon
        condition = Image.open(today['icon'])
        y = int(3 * self.box_TODAY['h'] / 4 - condition.size[1] / 2)
        x = int(self.box_TODAY['x'] + self.box_TODAY['w'] / 2 - condition.size[0] / 2)
        img.paste(condition, (x, y))

        # tomorrow's forecast
        # tomorrow's text
        draw.text((self.box_TOMORROW['x'] + self.BORDER, self.box_TOMORROW['y'] + self.BORDER), tomorrow['day'], font=self.font_small, fill=black)
        # low
        x = int(self.box_TOMORROW['w'] / 8)
        y = int(self.box_TOMORROW['y'] + 2 * self.box_TOMORROW['h'] / 3)
        print_temp((x, y), "low: ", tomorrow['low'], 1.5)
        # high
        x = int(2 * self.box_TOMORROW['w'] / 3)
        print_temp((x, y), "high: ", tomorrow['high'], 1.5)
        # condition icon
        condition = Image.open(tomorrow['icon'])
        y -= condition.size[1]
        x = int(self.box_TOMORROW['w'] / 2 - condition.size[0] / 2)
        img.paste(condition, (x, y))
        # condition description - under the icon
        condition_w, condition_h = draw.textsize(tomorrow['condition'], font=self.font_small)
        x = int(self.box_TOMORROW['w'] / 2 - condition_w / 2)
        y += condition.size[1] + 2 * self.BORDER
        draw.text((x, y), tomorrow['condition'], font=self.font_small, fill=gray)

        def print_other_days(dimensions, data):
            # day name
            day_w, day_h = draw.textsize(data['day'], font=self.font_small)
            x = int(dimensions['x'] + dimensions['w'] / 2 - day_w / 2)
            y = dimensions['y'] + self.BORDER
            draw.text((x, y), data['day'], font=self.font_small, fill=black)
            # low temp
            x = dimensions['x'] + self.BORDER
            y = int(dimensions['y'] + dimensions['h'] / 4)
            print_temp((x, y), "low: ", data['low'])
            # high temp
            y += int(dimensions['h'] / 4)
            print_temp((x, y), "high: ", data['high'])
            # condition icon
            condition = Image.open(data['icon'])
            y += 2 * self.BORDER
            x = int(dimensions['x'] + dimensions['w'] / 2 - condition.size[0] / 2)
            img.paste(condition, (x, y))
            # condition description
            condition_w, condition_h = draw.textsize(data['condition'], font=self.font_tiny)
            y += condition.size[1] + self.BORDER
            x = int(dimensions['x'] + dimensions['w'] / 2 - condition_w / 2)
            draw.text((x, y), data['condition'], font=self.font_tiny, fill=gray)

        # the next 3 days
        for i in range(3):
            print_other_days(self.boxes_NEXT_DAYS[i], days[i])

        # ip address
        ip_w, ip_h = draw.textsize(self.ip_address, font=self.font_tiny)
        draw.text((WIDTH - self.BORDER - ip_w, HEIGHT - self.BORDER - ip_h), self.ip_address, font=self.font_tiny, fill=gray)

        if "linux" in platform:
            img.save(tempfile.gettempdir() + "/img.bmp")
            return bytes(tempfile.gettempdir() + "/img.bmp", 'utf-8')
        else:
            img.save(tempfile.gettempdir() + "\\img.bmp")
            return bytes(tempfile.gettempdir() + "\\img.bmp", 'utf-8')

    def update(self):
        try:
            self.current = self.weather.get_weather_current()
            self.forecast = self.weather.get_weather_forecast()
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
        fbink.fbink_cls(self.fbfd, self.fbink_cfg, rect, 0)

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
            time.sleep(5 * 60)
            counter += 1
    finally:
        fbink.fbink_close(yawk.fbfd)


if __name__ == "__main__":
    main()
