import urllib2
import os
import tempfile
import time
from _fbink import ffi, lib as fbink
from PIL import Image, ImageDraw, ImageFont
import socket
from xml.dom.minidom import parseString
from datetime import datetime, timedelta
from subprocess import call
import configparser


CONFIGFILE = "config.ini"


print("YAWK started!")

    
def most_frequent(List):
    dict = {}
    count, itm = 0, ''
    for item in reversed(List):
        dict[item] = dict.get(item, 0) + 1
        if dict[item] >= count:
            count, itm = dict[item], item
    return (itm)


def get_weather_forecast(api_key, city_id, current_temperature):
    print("Getting weather forecast information . . .")

    weather_link = "http://api.openweathermap.org/data/2.5/forecast?id=" + \
                   city_id + \
                   "&units=metric&mode=xml&APPID=" + \
                   api_key
    weather_xml = urllib2.urlopen(weather_link)
    weather_data = weather_xml.read()
    weather_xml.close()

    '''
    file = open('weather.xml', 'w')
    if file is not None:
        file.write(weather_data)
        file.close()
    else:
        print("file not opened")
        return None
    file = open('weather.xml')
    weather_data = file.read()
    file.close()
    '''

    dom = parseString(weather_data)

    highs = []
    lows = []
    conditions = []
    icons = []

    times = dom.getElementsByTagName('time')

    today = datetime.today().strftime("%Y-%m-%d")

    for d in range(5):
        day = datetime.now() + timedelta(days=d)
        # day = datetime.now() + timedelta(days=d - 1)
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
        # print("{}: {} to {}, {}".format(day, min, max, most_frequent(day_condition)))
        lows.append(str(round(min, 1)))
        highs.append(str(round(max, 1)))
        conditions.append(most_frequent(day_condition))
        icons.append(most_frequent(icon))

    # minor fix for the temperature today...
    if lows[0] > current_temperature:
        lows[0] = current_temperature
    if highs[0] < current_temperature:
        highs[0] = current_temperature

    now = datetime.now()
    day2 = now + timedelta(days=1)
    day3 = now + timedelta(days=2)
    day4 = now + timedelta(days=3)
    day5 = now + timedelta(days=4)
    days = ["Today", day2.strftime("%A"), day3.strftime("%A"), day4.strftime("%A"), day5.strftime("%A")]

    # images
    img_links = []
    for icon in icons:
        link = "icons/" + icon + ".png"
        img_links.append(link)
        # print(link)

    # print(img_links)
    # print(highs, lows)
    # print(conditions)
    # print(days)
    
    data = [days, highs, lows, conditions, img_links]

    return data
    
def get_weather_current(api_key, city_id):

    print("Getting current weather information . . .")

    weather_link = "http://api.openweathermap.org/data/2.5/weather?id=" + \
                   city_id + \
                   "&units=metric&mode=xml&APPID=" + \
                   api_key
    weather_xml = urllib2.urlopen(weather_link)
    weather_data = weather_xml.read()
    weather_xml.close()

    '''
    file = open('weather_curr.xml', 'w')
    if file is not None:
        file.write(weather_data)
        file.close()
    else:
        print("file not opened")
        return None
    file = open('weather_curr.xml')
    weather_data = file.read()
    file.close()
    '''

    dom = parseString(weather_data)

    current_temperature = float(dom.getElementsByTagName('temperature')[0].getAttribute('value'))
    current_humidity = float(dom.getElementsByTagName('humidity')[0].getAttribute('value'))
    current_condition = dom.getElementsByTagName('weather')[0].getAttribute('value')
    current_icon = "icons/" + dom.getElementsByTagName('weather')[0].getAttribute('icon') + ".png"
    #current_icon = "icons/" + "10n" + ".png"
    current_wind = float(dom.getElementsByTagName('speed')[0].getAttribute('value'))
    current_wind_desc = dom.getElementsByTagName('speed')[0].getAttribute('name')
    
    data = {'temperature': str(round(current_temperature, 1)),
            'humidity': str(round(current_humidity, 0)),
            'wind_val': str(round(current_wind, 1)),
            'wind_desc': current_wind_desc,
            'condition': current_condition, 
            'icon': current_icon}

    return data


def create_raw_image(current, forecast):

    if forecast is not None and len(forecast) != 0:
        days = forecast[0]
        highs = forecast[1]
        lows = forecast[2]
        conditions = forecast[3]
        img_links = forecast[4]
    else:
        return ""
    
    print("Creating image . . .")

    WIDTH = 758     # 600
    HEIGHT = 1024   # 800
    # white = (255, 255, 255)
    # black = (0, 0, 0)
    # gray = (125, 125, 125)
    white = 255
    black = 0
    gray = 128
    
    img = Image.new('L', (WIDTH, HEIGHT), color=white)
    draw = ImageDraw.Draw(img, 'L')
    celsius_icon = Image.open('icons/C.png')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    
    tiny_font = ImageFont.truetype("fonts/Cabin-Regular.ttf", 22)
    small_font = ImageFont.truetype("fonts/Fabrica.otf", 26)
    font = ImageFont.truetype("fonts/Forum-Regular.ttf", 50)
    comfortaa = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 80)
    comfortaa_small = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 40)

    # Dividing lines
    # vertical - today's forecast
    draw.line([(8*WIDTH/12 - 20, 10), (8*WIDTH/12 - 20, HEIGHT/4 - 10)], gray)
    # horiz - top
    draw.line([(10, HEIGHT/4), (WIDTH-10, HEIGHT/4)], gray)
    # horiz - middle
    draw.line([(10, HEIGHT/2), (WIDTH-10, HEIGHT/2)], gray)
    # vert - left
    draw.line([(WIDTH/3, HEIGHT/2 + 10), (WIDTH/3, HEIGHT - 30)], gray)
    # vert - right
    draw.line([(2*WIDTH/3, HEIGHT/2 + 10), (2*WIDTH/3, HEIGHT - 30)], gray)
    
    # Current
    # time
    the_time = datetime.now().strftime("%Hh%M")
    draw.text((10, 10), the_time, font=small_font, fill=black)
    the_time_height = draw.textsize(the_time, font=small_font)[1]
    # temperature
    temp_font = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", 120)
    temp_width, temp_height = draw.textsize(current['temperature'], font=temp_font)
    draw.text((60, HEIGHT/8 - temp_height/2), current['temperature'], font=temp_font, fill=black)
    # celsius
    img.paste(celsius_icon, (60 + temp_width, HEIGHT/8 - temp_height/2))
    # wind description
    w = 8*WIDTH/12 - 20 - 10
    wind_desc_width, wind_desc_height = draw.textsize(" ({})".format(current['wind_desc']), font=tiny_font)
    w -= wind_desc_width
    h = HEIGHT/4 - wind_desc_height - 10
    draw.text((w, h), " ({})".format(current['wind_desc']), font=tiny_font, fill=gray)
    # wind value
    wind_val_width, wind_val_height = draw.textsize("{}m/s".format(current['wind_val']), font=small_font)
    w -= wind_val_width
    h = HEIGHT/4 - wind_val_height - 10
    draw.text((w, h), "{}m/s".format(current['wind_val']), font=small_font, fill=black)
    # wind
    wind_width, wind_height = draw.textsize("wind: ", font=tiny_font)
    w -= wind_width
    h = HEIGHT/4 - wind_height - 10
    draw.text((w, h), "wind: ", font=tiny_font, fill=gray)
    # humidity value
    w = 8*WIDTH/12 - 20 - 10
    hum_val_width, hum_val_height = draw.textsize("{}%".format(current['humidity']), font=small_font)
    w -= hum_val_width
    h = HEIGHT/4 - wind_val_height - 10 - hum_val_height - 10
    draw.text((w, h), "{}%".format(current['humidity']), font=small_font, fill=black)
    # humidity
    hum_width, hum_height = draw.textsize("humidity: ", font=tiny_font)
    w -= hum_width
    h = HEIGHT/4 - wind_val_height - 10 - hum_height - 10
    draw.text((w, h), "humidity: ", font=tiny_font, fill=gray)
    # condition icon
    condition  = Image.open(current['icon'])
    img.paste(condition, (WIDTH/2 - condition.width/2, HEIGHT/8 - 3*condition.height/4))
    # condition
    condition_width = draw.textsize(current['condition'], font=small_font)[0]
    draw.text((8*WIDTH/12 - 20 - condition_width - 20, 15), current['condition'], font=small_font)
    
    
    # Today - Forecast
    # today string
    today_size = draw.textsize(days[0], font=small_font)[0]
    today_size_height = draw.textsize(days[0], font=small_font)[1]
    draw.text((WIDTH - WIDTH/4, 15), days[0], font=small_font, fill=black)
    # low string
    draw.text((8*WIDTH/12, 15 + today_size_height + 20), "low: ", font=small_font, fill=gray)
    low_size = draw.textsize("low: ", font=small_font)[0]
    # low temp string
    draw.text((8*WIDTH/12 + low_size, 15 + today_size_height + 20), lows[0], font=comfortaa, fill=black)
    low_temp_size = draw.textsize(lows[0], font=comfortaa)[0]
    low_temp_height = draw.textsize(lows[0], font=comfortaa)[1]
    #celsius
    img.paste(celsius_icon, (8*WIDTH/12 + low_size + low_temp_size, 15 + today_size_height + 20))
    # high string
    draw.text((8*WIDTH/12, 15 + today_size_height + 20 + low_temp_height + 20), "high: ", font=small_font, fill=gray)
    high_size = draw.textsize("high: ", font=small_font)[0]
    # high temp string
    draw.text((8*WIDTH/12 + high_size, 15 + today_size_height + 20 + low_temp_height + 20), highs[0], font=comfortaa, fill=black)
    high_temp_size = draw.textsize(highs[0], font=comfortaa)[0]
    high_temp_height = draw.textsize(highs[0], font=comfortaa)[1]
    # celsius
    img.paste(celsius_icon, (8*WIDTH/12 + high_size + high_temp_size, 15 + today_size_height + 20 + low_temp_height + 20))
    # condition
    cond_size = draw.textsize(conditions[0], font=small_font)[0]
    draw.text((WIDTH - cond_size - 10, 15 + today_size_height + 20 + low_temp_height + 20 + high_temp_height + 15), conditions[0], font=small_font, fill=black)
    
    # Tomorrow
    # day string
    draw.text((10, HEIGHT/4 + 15), days[1], font=small_font, fill=black)
    # high string
    draw.text((WIDTH/12, HEIGHT/4 + HEIGHT/8), "high: ", font=small_font, fill=black)
    high_size = draw.textsize("high: ", font=small_font)[0]
    # high temp string
    draw.text((WIDTH/12 + high_size, HEIGHT/4 + HEIGHT/8), highs[1], font=comfortaa, fill=black)
    high_temp_size = draw.textsize(highs[1], font=comfortaa)[0]
    # celsius
    img.paste(celsius_icon, (WIDTH/12 + high_size + high_temp_size, HEIGHT/4 + HEIGHT/8))
    # low string
    draw.text((8*WIDTH/12, HEIGHT/4 + HEIGHT/8), "low: ", font=small_font, fill=black)
    low_size = draw.textsize("low: ", font=small_font)[0]
    # low temp string
    draw.text((8*WIDTH/12 + low_size, HEIGHT/4 + HEIGHT/8), lows[1], font=comfortaa, fill=black)
    low_temp_size = draw.textsize(lows[1], font=comfortaa)[0]
    #celsius
    img.paste(celsius_icon, (8*WIDTH/12 + low_size + low_temp_size, HEIGHT/4 + HEIGHT/8))
    # condition
    cond_size = draw.textsize(conditions[1], font=font)[0]
    draw.text((WIDTH/2 - cond_size/2, HEIGHT/4 + 15), conditions[1], font=font, fill=black)
    # condition icon
    condition  = Image.open(img_links[1])
    img.paste(condition, (WIDTH/2 - condition.width/2, HEIGHT/4 + HEIGHT/4 - HEIGHT/8 - condition.height/4))
    
    # Day 3
    # day string
    day_size = draw.textsize(days[2], font=small_font)[0]
    draw.text((WIDTH/6 - day_size/2, HEIGHT/2 + 15), days[2], font=small_font, fill=black)
    # high string
    draw.text((WIDTH/16, HEIGHT - HEIGHT/6), "high: ", font=small_font, fill=black)
    high_size = draw.textsize("high: ", font=small_font)[0]
    # high temp string
    draw.text((WIDTH/16 + high_size, HEIGHT - HEIGHT/6), highs[2], font=comfortaa_small, fill=black)
    high_temp_size = draw.textsize(highs[2], font=comfortaa_small)[0]
    # celsius
    img.paste(celsius_icon, (WIDTH/16 + high_size + high_temp_size, HEIGHT - HEIGHT/6))
    # low string
    draw.text((WIDTH/16, HEIGHT - HEIGHT/10), "low: ", font=small_font, fill=black)
    low_size = draw.textsize("low: ", font=small_font)[0]
    # low temp string
    draw.text((WIDTH/16 + low_size, HEIGHT - HEIGHT/10), lows[2], font=comfortaa_small, fill=black)
    low_temp_size = draw.textsize(lows[2], font=comfortaa_small)[0]
    #celsius
    img.paste(celsius_icon, (WIDTH/16 + low_size + low_temp_size, HEIGHT - HEIGHT/10))
    # condition
    cond_size = draw.textsize(conditions[2], font=tiny_font)[0]
    draw.text((WIDTH/6 - cond_size/2, HEIGHT/2 + 60), conditions[2], font=tiny_font, fill=black)
    # condition icon
    condition  = Image.open(img_links[2])
    img.paste(condition, (WIDTH/6 - condition.width/2, HEIGHT - HEIGHT/3 - condition.height/6))
    
    # Day 4
    # day string
    day_size = draw.textsize(days[3], font=small_font)[0]
    draw.text((WIDTH/3 + WIDTH/6 - day_size/2, HEIGHT/2 + 15), days[3], font=small_font, fill=black)
    # high string
    draw.text((WIDTH/3 + WIDTH/16, HEIGHT - HEIGHT/6), "high: ", font=small_font, fill=black)
    high_size = draw.textsize("high: ", font=small_font)[0]
    # high temp string
    draw.text((WIDTH/3 + WIDTH/16 + high_size, HEIGHT - HEIGHT/6), highs[3], font=comfortaa_small, fill=black)
    high_temp_size = draw.textsize(highs[3], font=comfortaa_small)[0]
    # celsius
    img.paste(celsius_icon, (WIDTH/3 + WIDTH/16 + high_size + high_temp_size, HEIGHT - HEIGHT/6))
    # low string
    draw.text((WIDTH/3 + WIDTH/16, HEIGHT - HEIGHT/10), "low: ", font=small_font, fill=black)
    low_size = draw.textsize("low: ", font=small_font)[0]
    # low temp string
    draw.text((WIDTH/3 + WIDTH/16 + low_size, HEIGHT - HEIGHT/10), lows[3], font=comfortaa_small, fill=black)
    low_temp_size = draw.textsize(lows[3], font=comfortaa_small)[0]
    #celsius
    img.paste(celsius_icon, (WIDTH/3 + WIDTH/16 + low_size + low_temp_size, HEIGHT - HEIGHT/10))
    # condition
    cond_size = draw.textsize(conditions[3], font=tiny_font)[0]
    draw.text((WIDTH/3 + WIDTH/6 - cond_size/2, HEIGHT/2 + 60), conditions[3], font=tiny_font, fill=black)
    # condition icon
    condition  = Image.open(img_links[3])
    img.paste(condition, (WIDTH/3 + WIDTH/6 - condition.width/2, HEIGHT - HEIGHT/3 - condition.height/6))
    
    # Day 5
    # day string
    day_size = draw.textsize(days[4], font=small_font)[0]
    draw.text((2*WIDTH/3 + WIDTH/6 - day_size/2, HEIGHT/2 + 15), days[4], font=small_font, fill=black)
    # high string
    draw.text((2*WIDTH/3 + WIDTH/16, HEIGHT - HEIGHT/6), "high: ", font=small_font, fill=black)
    high_size = draw.textsize("high: ", font=small_font)[0]
    # high temp string
    draw.text((2*WIDTH/3 + WIDTH/16 + high_size, HEIGHT - HEIGHT/6), highs[4], font=comfortaa_small, fill=black)
    high_temp_size = draw.textsize(highs[4], font=comfortaa_small)[0]
    # celsius
    img.paste(celsius_icon, (2*WIDTH/3 + WIDTH/16 + high_size + high_temp_size, HEIGHT - HEIGHT/6))
    # low string
    draw.text((2*WIDTH/3 + WIDTH/16, HEIGHT - HEIGHT/10), "low: ", font=small_font, fill=black)
    low_size = draw.textsize("low: ", font=small_font)[0]
    # low temp string
    draw.text((2*WIDTH/3 + WIDTH/16 + low_size, HEIGHT - HEIGHT/10), lows[4], font=comfortaa_small, fill=black)
    low_temp_size = draw.textsize(lows[4], font=comfortaa_small)[0]
    #celsius
    img.paste(celsius_icon, (2*WIDTH/3 + WIDTH/16 + low_size + low_temp_size, HEIGHT - HEIGHT/10))
    # condition
    cond_size = draw.textsize(conditions[4], font=tiny_font)[0]
    draw.text((2*WIDTH/3 + WIDTH/6 - cond_size/2, HEIGHT/2 + 60), conditions[4], font=tiny_font, fill=black)
    # condition icon
    condition  = Image.open(img_links[4])
    img.paste(condition, (2*WIDTH/3 + WIDTH/6 - condition.width/2, HEIGHT - HEIGHT/3 - condition.height/6))
    
    # time updated
    update_time = "Last updated at " + datetime.now().strftime("%H:%M")
    draw.text((10, HEIGHT-35), update_time, font=tiny_font, fill=gray)
    
    # ip address
    ip_size = draw.textsize(ip_address, font=tiny_font)[0]
    draw.text((WIDTH - 10 - ip_size, HEIGHT-35), ip_address, font=tiny_font, fill=gray)
    
    img.save(tempfile.gettempdir() + "/img.png")
    return tempfile.gettempdir() + "/img.png"
    

def wakeup_wifi():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return
    except Exception as e:
        print("exc. ignored {}".format(e))
    
    while True:
        call(["ifconfig","eth0","down"])
        time.sleep(5)
        call(["ifconfig","eth0","up"])
        time.sleep(15)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return
        except Exception as e:
            print("exc. ignored {}".format(e))

def get_config_data(configfile):
    config = configparser.RawConfigParser()
    config.read(configfile)
    api_key = config.get("yawk", "key")
    city_id = config.get("yawk", "city")

    print("api: {}\ncity: {}".format(api_key, city_id))

    return api_key, city_id


api_key, city_id = get_config_data(CONFIGFILE)

fbink_cfg = ffi.new("FBInkConfig *")
fbink_cfg.is_centered = True
fbink_cfg.is_halfway = True

fbfd = fbink.fbink_open()
fbink.fbink_init(fbfd, fbink_cfg)

try:
    call(["hostname","kobo"])
    while True:
        wakeup_wifi()

        current = get_weather_current(api_key, city_id)
        forecast = get_weather_forecast(api_key, city_id, current['temperature'])
        image = create_raw_image(current, forecast)
        fbink.fbink_cls(fbfd, fbink_cfg)
        fbink.fbink_print_image(fbfd, image, 0, 0, fbink_cfg)
        time.sleep(5 * 60)
finally:
    fbink.fbink_close(fbfd)

