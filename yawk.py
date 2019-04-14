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

    data = []

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
        data.append({'low': str(round(min, 1)), 
                     'high': str(round(max, 1)),
                     'condition': most_frequent(day_condition),
                     'icon': "icons/" + most_frequent(icon) + ".png",
                     'day': (datetime.now() + timedelta(days=d)).strftime("%A")
                     })

    # minor fix for the temperature today...
    if data[0]['low'] > current_temperature:
        data[0]['low'] = current_temperature
    if data[0]['high'] < current_temperature:
        data[0]['high'] = current_temperature

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

    city_name = dom.getElementsByTagName('city')[0].getAttribute('name')
    country_code = dom.getElementsByTagName('country')[0].firstChild.nodeValue
    current_temperature = float(dom.getElementsByTagName('temperature')[0].getAttribute('value'))
    current_humidity = dom.getElementsByTagName('humidity')[0].getAttribute('value')
    current_condition = dom.getElementsByTagName('weather')[0].getAttribute('value')
    current_icon = "icons/" + dom.getElementsByTagName('weather')[0].getAttribute('icon') + ".png"
    #current_icon = "icons/" + "10n" + ".png"
    current_wind = float(dom.getElementsByTagName('speed')[0].getAttribute('value'))*3.6
    current_wind_desc = dom.getElementsByTagName('speed')[0].getAttribute('name')
    
    data = {'city': city_name + ", " + country_code,
            'temperature': str(round(current_temperature, 1)),
            'humidity': current_humidity + "%",
            'wind_val': str(int(round(current_wind, 0))) + "km/h",
            'wind_desc': current_wind_desc,
            'condition': current_condition, 
            'icon': current_icon}

    return data


def create_raw_image(screen_size, current, forecast):

    if forecast is not None and len(forecast) != 0:
        today = forecast[0]
        tomorrow = forecast[1]
        days = forecast[2:]
    else:
        return ""
    
    print("Creating image . . .")

    # 758 x 1024
    WIDTH = screen_size[0]
    HEIGHT = screen_size[1]
    
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
    header = current['city'] + ", " + datetime.now().strftime("%d.%m.%y, %Hh%M")
    header_w, header_h = draw.textsize(header, font=small_font)
    draw.text((CURRENT['w']/2 - header_w/2, BORDER), header, font=small_font, fill=black)
    # temperature
    temp_font = ImageFont.truetype("fonts/Comfortaa-Regular.ttf", HEIGHT/8)
    temp_w, temp_h = draw.textsize(current['temperature'], font=temp_font)
    draw.text((BORDER*3, 2*CURRENT['h']/7), current['temperature'], font=temp_font, fill=black)
    # celsius
    img.paste(celsius_icon.resize((celsius_icon.size[0]*2, celsius_icon.size[1]*2)), (BORDER*3 + temp_w, 2*CURRENT['h']/7))
    # condition icon
    condition  = Image.open(current['icon'])
    condition = condition.resize((int(condition.size[0]*1.2), int(condition.size[1]*1.2)))
    temp_end_x = BORDER*3 + temp_w + celsius_icon.size[0]*2
    x = (CURRENT['w'] + temp_end_x)/2 - int(condition.size[0]/2)
    img.paste(condition, (x, CURRENT['h']/2 - int(condition.size[1]/2)))
    # condition description - under the icon?
    condition_w, condition_h = draw.textsize(current['condition'], font=small_font)
    x = (CURRENT['w'] + temp_end_x)/2 - condition_w/2
    y = CURRENT['h']/2 + int(condition.size[1]/2) + 3*BORDER
    draw.text((x, y), current['condition'], font=small_font, fill=gray)
    # wind icon
    y = CURRENT['h'] - wind_icon.size[1]
    img.paste(wind_icon, (BORDER, y))
    # wind value
    wind_w, wind_h = draw.textsize(current['wind_val'], font=small_font)
    y = y + wind_icon.size[1]/2 - wind_h/2
    draw.text((BORDER + wind_icon.size[0] + BORDER, y), current['wind_val'], font=small_font, fill=black)
    # humidity icon
    y = CURRENT['h'] - wind_icon.size[1] - humidity_icon.size[1]
    x = BORDER + wind_icon.size[0]/2 - humidity_icon.size[0]/2
    img.paste(humidity_icon, (x, y))
    # humidity value
    humidity_w, humidity_h = draw.textsize(current['humidity'], font=small_font)
    y = y + humidity_icon.size[1]/2 - humidity_h/2
    draw.text((BORDER + wind_icon.size[0] + BORDER, y), current['humidity'], font=small_font, fill=black)
    
    def print_temp(position, text, temp, scale = 1.0):
        # text string
        text_w, text_h = draw.textsize(text, font=small_font)
        y = position[1] - text_h
        x = position[0]
        draw.text((x, y), text, font=small_font, fill=gray)
        # low value
        temp_w, temp_h = draw.textsize(temp, font=comfortaa)
        y = y + text_h - temp_h
        x += text_w
        draw.text((x,y), temp, font=comfortaa, fill=black)
        # celsius
        x += temp_w
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
        call(["./utils/wifidown.sh"])
        time.sleep(5)
        call(["./utils/wifiup.sh"])
        time.sleep(20)
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


def main():
    api_key, city_id = get_config_data(CONFIGFILE)

    fbink_cfg = ffi.new("FBInkConfig *")
    fbink_cfg.is_centered = True
    fbink_cfg.is_halfway = True

    fbfd = fbink.fbink_open()
    fbink.fbink_init(fbfd, fbink_cfg)
    state = ffi.new("FBInkState *")
    fbink.fbink_get_state(fbink_cfg, state)

    screen_size = (state.screen_width, state.screen_height)

    try:
        call(["hostname","kobo"])
        while True:
            wakeup_wifi()

            current = get_weather_current(api_key, city_id)
            forecast = get_weather_forecast(api_key, city_id, current['temperature'])
            image = create_raw_image(screen_size, current, forecast)
            fbink.fbink_cls(fbfd, fbink_cfg)
            fbink.fbink_print_image(fbfd, image, 0, 0, fbink_cfg)
            time.sleep(5 * 60)
    finally:
        fbink.fbink_close(fbfd)

if __name__ == "__main__":
    main()
