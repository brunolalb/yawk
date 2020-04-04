from sys import platform
import socket
import tempfile
import time
from PIL import Image, ImageDraw, ImageFont
from subprocess import call
import configparser
import argparse
from datetime import datetime
from weather import yawkWeather
try:
    from _fbink import ffi, lib as fbink
except ImportError:
    from fbink_mock import ffi, lib as fbink


CONFIGFILE = "config.ini"


class YAWK():
    def __init__(self, xml_save_file, xml_read_file):
        self.cfg_data = dict()
        cfg_file_data = self._get_config_data(CONFIGFILE)
        self.cfg_data['api'] = cfg_file_data['api_key']
        self.cfg_data['city'] = cfg_file_data['city_id']
        self.cfg_data['save_data'] = xml_save_file
        self.cfg_data['xml_file'] = xml_read_file

        self.fbink_cfg = ffi.new("FBInkConfig *")
        self.fbink_cfg.is_centered = True
        self.fbink_cfg.is_halfway = True

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

        try:
            self.weather = yawkWeather(self.cfg_data)
        except Exception:
            fbink.fbink_close(self.fbfd)

    def _create_raw_image(self):

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

        ICON_SIZE = (HEIGHT/8, HEIGHT/8)

        white = 255
        black = 0
        gray = 128

        BORDER = 10

        # Boxes positions
        # current condition
        CURRENT = {'x': 0, 'y': 0, 'w': 2*WIDTH/3, 'h': HEIGHT/3}
        # today's forecast
        TODAY = {'x': CURRENT['w'], 'y': 0, 'w': WIDTH - CURRENT['w'], 'h': CURRENT['h']}
        # tomorrow
        TOMORROW = {'x': 0, 'y': CURRENT['h'], 'w': WIDTH, 'h': (HEIGHT - CURRENT['h'])/3}
        # next 3 days
        NEXT_DAYS = [{'x': 0, 'y': CURRENT['h'] + TOMORROW['h'], 'w': WIDTH/3, 'h': HEIGHT - CURRENT['h'] - TOMORROW['h']}]
        NEXT_DAYS.append({'x': NEXT_DAYS[0]['w'], 'y': NEXT_DAYS[0]['y'], 'w': NEXT_DAYS[0]['w'], 'h': NEXT_DAYS[0]['h']})
        NEXT_DAYS.append({'x': NEXT_DAYS[1]['x'] + NEXT_DAYS[1]['w'], 'y': NEXT_DAYS[1]['y'], 'w': NEXT_DAYS[1]['w'], 'h': NEXT_DAYS[1]['h']})

        img = Image.new('L', (WIDTH, HEIGHT), color=white)
        draw = ImageDraw.Draw(img, 'L')
        celsius_icon = Image.open('icons/C.png')
        wind_icon = Image.open('icons/w.png')
        humidity_icon = Image.open('icons/h.png')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]

        tiny_font = ImageFont.truetype("fonts/Cabin-Regular.ttf", 22)
        small_font = ImageFont.truetype("fonts/Fabrica.otf", 26)
        font = ImageFont.truetype("fonts/Forum-Regular.ttf", 50)
        comfortaa = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 80)
        comfortaa_small = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 40)

        # Dividing lines
        # under today/current
        draw.line([(BORDER, CURRENT['h']), (WIDTH - BORDER, CURRENT['h'])], gray)
        # between today/current
        draw.line([(CURRENT['w'], BORDER), (CURRENT['w'], CURRENT['h'] - BORDER)], gray)
        # under tomorrow
        draw.line([(BORDER, NEXT_DAYS[0]['y']), (WIDTH - BORDER, NEXT_DAYS[0]['y'])], gray)
        # between day 3/4
        draw.line([(NEXT_DAYS[1]['x'], NEXT_DAYS[1]['y'] + BORDER), (NEXT_DAYS[1]['x'], HEIGHT - BORDER)], gray)
        # between day 4/5
        draw.line([(NEXT_DAYS[2]['x'], NEXT_DAYS[2]['y'] + BORDER), (NEXT_DAYS[2]['x'], HEIGHT - BORDER)], gray)

        # Current conditions
        # City Name, Country Code, Day, Time
        header = self.current['city'] + ", " + datetime.now().strftime("%d.%m.%y, %Hh%M")
        header_w, header_h = draw.textsize(header, font=small_font)
        draw.text((CURRENT['w']/2 - header_w/2, BORDER), header, font=small_font, fill=black)
        # temperature
        temp_font = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", HEIGHT/8)
        temp_w, temp_h = draw.textsize(self.current['temperature'], font=temp_font)
        draw.text((BORDER*3, 2*CURRENT['h']/7), self.current['temperature'], font=temp_font, fill=black)
        # celsius
        img.paste(celsius_icon.resize((celsius_icon.size[0]*2, celsius_icon.size[1]*2)), (BORDER*3 + temp_w, 2*CURRENT['h']/7))
        # condition icon
        condition  = Image.open(self.current['icon'])
        condition = condition.resize((int(condition.size[0]*1.2), int(condition.size[1]*1.2)))
        temp_end_x = BORDER*3 + temp_w + celsius_icon.size[0]*2
        x = (CURRENT['w'] + temp_end_x)/2 - int(condition.size[0]/2)
        img.paste(condition, (x, CURRENT['h']/2 - int(condition.size[1]/2)))
        # condition description - under the icon?
        condition_w, condition_h = draw.textsize(self.current['condition'], font=small_font)
        x = (CURRENT['w'] + temp_end_x)/2 - condition_w/2
        y = CURRENT['h']/2 + int(condition.size[1]/2) + 3*BORDER
        draw.text((x, y), self.current['condition'], font=small_font, fill=gray)
        # wind icon
        y = CURRENT['h'] - wind_icon.size[1]
        img.paste(wind_icon, (BORDER, y))
        # wind value
        wind_w, wind_h = draw.textsize(self.current['wind_val'], font=small_font)
        y = y + wind_icon.size[1]/2 - wind_h/2
        draw.text((BORDER + wind_icon.size[0] + BORDER, y), self.current['wind_val'], font=small_font, fill=black)
        # humidity icon
        y = CURRENT['h'] - wind_icon.size[1] - humidity_icon.size[1]
        x = BORDER + wind_icon.size[0]/2 - humidity_icon.size[0]/2
        img.paste(humidity_icon, (x, y))
        # humidity value
        humidity_w, humidity_h = draw.textsize(self.current['humidity'], font=small_font)
        y = y + humidity_icon.size[1]/2 - humidity_h/2
        draw.text((BORDER + wind_icon.size[0] + BORDER, y), self.current['humidity'], font=small_font, fill=black)

        def print_temp(pos, text, temp, scale=1.0):
            # text string
            text_w, text_h = draw.textsize(text, font=small_font)
            y = pos[1] - text_h
            x = pos[0]
            draw.text((x, y), text, font=small_font, fill=gray)
            # low value
            temp_width, temp_height = draw.textsize(temp, font=comfortaa)
            y = y + text_h - temp_height
            x += text_w
            draw.text((x, y), temp, font=comfortaa, fill=black)
            # celsius
            x += temp_width
            img.paste(celsius_icon.resize((int(celsius_icon.size[0]*scale), int(celsius_icon.size[1]*scale))), (x, y))

        # today's forecast
        # low temperature
        position = [TODAY['x'] + BORDER, TODAY['h']/4]
        print_temp(position, "low: ", today['low'], 1.3)
        # high temperature
        position = [TODAY['x'] + BORDER, 2*TODAY['h']/4]
        print_temp(position, "high: ", today['high'], 1.3)
        # condition icon
        condition  = Image.open(today['icon'])
        y = 3*TODAY['h']/4 - condition.size[1]/2
        x = TODAY['x'] + TODAY['w']/2 - condition.size[0]/2
        img.paste(condition, (x, y))

        # tomorrow's forecast
        # tomorrow's text
        draw.text((TOMORROW['x'] + BORDER, TOMORROW['y'] + BORDER), tomorrow['day'], font=small_font, fill=black)
        # low
        x = TOMORROW['w']/8
        y = TOMORROW['y'] + 2*TOMORROW['h']/3
        print_temp((x, y), "low: ", tomorrow['low'], 1.5)
        # high
        x = 2*TOMORROW['w']/3
        print_temp((x, y), "high: ", tomorrow['high'], 1.5)
        # condition icon
        condition  = Image.open(tomorrow['icon'])
        y -= condition.size[1]
        x = TOMORROW['w']/2 - condition.size[0]/2
        img.paste(condition, (x, y))
        # condition description - under the icon
        condition_w, condition_h = draw.textsize(tomorrow['condition'], font=small_font)
        x = TOMORROW['w']/2 - condition_w/2
        y += condition.size[1] + 2*BORDER
        draw.text((x, y), tomorrow['condition'], font=small_font, fill=gray)

        def print_other_days(dimensions, data):
            # day name
            day_w, day_h = draw.textsize(data['day'], font=small_font)
            x = dimensions['x'] + dimensions['w']/2 - day_w/2
            y = dimensions['y'] + BORDER
            draw.text((x, y), data['day'], font=small_font, fill=black)
            # low temp
            x = dimensions['x'] + BORDER
            y = dimensions['y'] + dimensions['h']/4
            print_temp((x, y), "low: ", data['low'])
            # high temp
            y += dimensions['h']/4
            print_temp((x, y), "high: ", data['high'])
            # condition icon
            condition = Image.open(data['icon'])
            y += 2*BORDER
            x = dimensions['x'] + dimensions['w']/2 - condition.size[0]/2
            img.paste(condition, (x, y))
            # condition description
            condition_w, condition_h = draw.textsize(data['condition'], font=tiny_font)
            y += condition.size[1] + BORDER
            x = dimensions['x'] + dimensions['w']/2 - condition_w/2
            draw.text((x, y), data['condition'], font=tiny_font, fill=gray)

        # the next 3 days
        for i in range(3):
            print_other_days(NEXT_DAYS[i], days[i])

        # ip address
        ip_w, ip_h = draw.textsize(ip_address, font=tiny_font)
        draw.text((WIDTH - BORDER - ip_w, HEIGHT - BORDER - ip_h), ip_address, font=tiny_font, fill=gray)

        if "linux" in platform:
            img.save(tempfile.gettempdir() + "/img.bmp")
            return tempfile.gettempdir() + "/img.bmp"
        else:
            img.save(tempfile.gettempdir() + "\\img.bmp")
            return tempfile.gettempdir() + "\\img.bmp"

        # bytes_io = BytesIO(img.tobytes())
        # raw_data = bytes_io.getvalue()

        # return img.tobytes()

    @staticmethod
    def _get_config_data(file_path):
        """turns the config file data into a dictionary"""
        parser = configparser.RawConfigParser()
        parser.read(file_path)
        data = dict()
        data['api_key'] = parser.get("yawk", "key")
        data['city_id'] = parser.get("yawk", "city")

        print("api: {}\ncity: {}".format(data['api_key'], data['city_id']))

        return data

    @staticmethod
    def wait_for_wifi():
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                return
            except Exception as e:
                print("exc. ignored {}".format(e))
            time.sleep(15)

    def update(self):
        self.wait_for_wifi()

        self.current = self.weather.get_weather_current()
        if self.current is None:
            return
        self.forecast = self.weather.get_weather_forecast()
        if self.forecast is None:
            return
        image = self._create_raw_image()
        fbink.fbink_cls(self.fbfd, self.fbink_cfg)

        # raw = image
        # fbink.fbink_print_raw_data(fbfd, raw, screen_size[0]*screen_size[1], screen_size[0], screen_size[1], 0, 0, fbink_cfg)

        fbink.fbink_print_image(self.fbfd, image, 0, 0, self.fbink_cfg)


def main():
    print("YAWK started!")

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--save', help='save XML file', action='store_true')
    parser.add_argument('-f', '--file', help='use the xml files instead of the API', action='store_true')
    args = parser.parse_args()

    if "linux" in platform:
        call(["hostname", "kobo"])

    YAWK.wait_for_wifi()

    if "linux" in platform:
        call(["killall", "-TERM", "nickel", "hindenburg", "sickel", "fickel"])

    try:
        yawk = YAWK(args.save, args.file)

        while True:
            yawk.update()
            time.sleep(5 * 60)
    finally:
        fbink.fbink_close(yawk.fbfd)

if __name__ == "__main__":
    main()

