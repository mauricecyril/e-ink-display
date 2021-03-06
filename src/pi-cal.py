#! /home/pi/python_programs/pi-cal/src/pi-cal.py

import calendar
import epd7in5
import datetime
import json
# import os
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
# from pprint import pprint
import requests
# import sys
import time

# print(os.getcwd())  # current working directory, absolute path
# print(sys.argv[0])  # working directory

global draw
global epd
global image
global EPD_HEIGHT
global EPD_WIDTH
global creds
global token
global weather

def main():
    print('main')
    init_display()
    
    with open('./credentials.json') as f:
        global creds
        creds = json.load(f)

    try:
        # If we've authenticated before, we'll have a token.json file
        with open('./token.json') as f:
            global token
            token = f
            Auth().auth_refresh()
    except:
        # Otherwise, we'll need to start a fresh authentication
        Auth.auth_request()
        Auth.auth_poll()

    draws = Draws()
    events = Events()

    events.fetch_events()
    events.fetch_weather()
    draws.draw_calendar()
    draws.draw_date()
    draws.draw_events()
    draws.draw_weather()
    render()

def init_display():
    print('init display')
    global EPD_WIDTH
    EPD_WIDTH = 640
    global EPD_HEIGHT
    EPD_HEIGHT = 384

    # Initialize E-Paper Display inferface
    global epd
    epd = epd7in5.EPD()
    epd.init()

    # For simplicity, the arguments are explicit numerical coordinates
    global image
    image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)    # 1: clear the frame
    global draw
    draw = ImageDraw.Draw(image)

class Auth:
    auth_response = None
    device_code = None

    def auth_request(self):
        print('auth request')
        global creds

        # Initial request
        auth_response = requests.post(creds['auth_url'], data = {
            'client_id': creds['client_id'],
            'scope': creds['scopes']
        }).json()

        # response = {
        #   'device_code': 'AH-1Ng1BzvzcVPXWrakudSRlaBkKTm5otqDWNT0u0p5J9mjXR1hMiS-rUS5D7Ss7LvDvAumcQReo_ME9N30vcEWiLbMQq0ORCw',    # Code unique to device so user can distinguish between them for access granting/revoking
        #   'expires_in': 1800,     # How long, in seconds, until the access token expires
        #   'interval': 5,  # How long, in seconds, you should wait before re-polling auth URL for auth success response
        #   'user_code': 'KQTW-SDMD',       # 
        #   'verification_url': 'https://www.google.com/device'     # Never changes as far as I know
        # }

        device_code = auth_response['device_code']

        # Render device auth codes
        group_top = 116

        draw.text((24, group_top), 'Visit', font = getFont(18, 'Regular'), fill = 0)
        draw.text((24, 32 + group_top), auth_response['verification_url'], font = getFont(24, 'Bold'), fill = 0)
        draw.text((24, 90 + group_top), 'and enter', font = getFont(18, 'Regular'), fill = 0)
        draw.text((24, 122 + group_top), auth_response['user_code'], font = getFont(32, 'Bold'), fill = 0)

        render()

    def auth_poll(self):
        print('auth poll')
        global creds

        def request_token():
            # Token polling
            return requests.post(creds['token_url'], data = {
                'client_id': creds['client_id'],
                'client_secret': creds['client_secret'],
                'code': creds['device_code'],
                'grant_type': creds['grant_type']
            })

        token_response = request_token()

        # token_response = {
        #     "access_token":"1/fFAGRNJru1FTz70BzhT3Zg",
        #     "expires_in":3920,
        #     "token_type":"Bearer",
        #     "refresh_token":"1/xEoDL4iW3cxlI7yDbSRFYNG01kVKM2C-259HOF2aQbI"
        # }

        # Poll Google API for auth confirmation token (after user accepts on separate device)
        interval = auth_response['interval']
        time.sleep(interval)

        i = 0

        while i < auth_response['expires_in'] and not token_response.ok:
            token_response = request_token()

            if token_response.ok:
                break
            # elif token_response == 403 or token_response == 400:
            else:
                time.sleep(interval)
                i += interval

        # Store token
        print('Auth successful!')
        
        with open('token.json', 'w') as fp:
            json.dump(token_response.json(), fp)

    def auth_refresh(self):
        print('auth refresh')

        access_token = requests.post(creds['refresh_url'], data = {
            'client_id': creds['client_id'],
            'client_secret': creds['client_secret'],
            'grant_type': 'refresh_token',
            'refresh_token': creds['refresh_token']
        }).json()

        # response = {
        #     "access_token":"1/fFAGRNJru1FTz70BzhT3Zg",
        #     "expires_in":3920,
        #     "token_type":"Bearer"
        # }

        global token
        token = access_token

        with open('token.json', 'w') as fp:
            json.dump(access_token, fp)

        print('refresh successful!')

class Events:
    def fetch_events(self):
        print('fetch events')
        global creds
        global events
        global token

        events_url = 'https://www.googleapis.com/calendar/v3/calendars/{}/events'.format(creds['calendar_id'])
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time

        events_response = requests.get(events_url, 
            headers = {
                'Authorization': '{} {}'.format(token['token_type'], token['access_token'])
            },
            params = {
                'maxResults': 8,
                'orderBy': 'startTime',
                'singleEvents': True,
                'timeMin': now
            }
        ).json()['items']

        events = self.format_events(events_response)
    
    def fetch_weather(self):
        print('fetch weather')
        payload = {
            'APPID': 'c12a8b60afb362193fd301b835f901dd',
            # 'id': 4781756,     # City ID for City of Richmond
            'units': 'imperial',
            'zip': 23223
        }

        weather_response = requests.get('http://api.openweathermap.org/data/2.5/weather', params = payload).json()
        
        global weather 
        weather = {
            'temperature': '{}°'.format(round(weather_response['main']['temp'])),
            'weather': weather_response['weather'][0]['id']
        }
        # print(temperature, weather)

    def format_events(self, events):
        print('format events')
        events_format = {}

        for event in events:
            event_YMD = ''

            # Get our date, formatted as YYYY-MM-DD
            try:
                event_YMD = datetime.datetime.strptime(event['start']['dateTime'][0:10], '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                event_YMD = datetime.datetime.strptime(event['start']['date'][0:10], '%Y-%m-%d').strftime('%Y-%m-%d')

            # Format a new dictionary with the date as key & events list as value
            try:
                events_format[event_YMD].append(event)
            except:
                events_format[event_YMD] = [event]

        return events_format

def getFont(size, weight):
    return ImageFont.truetype('/home/pi/python_programs/pi-cal/src/fonts/OpenSans-{}.ttf'.format(weight), size)

class Draws():    
    def draw_calendar(self):
        print('draw calendar')

        now = datetime.datetime.now()
        today = now.day
        year = now.year
        month = now.month
        month_str = now.strftime('%B')
        calendar_top = 192
        cal = calendar.Calendar(calendar.SUNDAY)
        days_in_weeks = cal.monthdayscalendar(year, month)

        # Calendar title. Gotta do some trickery to center-align text
        calendar_title_font = getFont(20, 'Regular')
        calendar_title_text = '{} {}'.format(month_str, year)
        calendar_title_w = calendar_title_font.getsize(calendar_title_text)[0]
        calendar_title_x = (190 / 2) - (calendar_title_w / 2)
        draw.text((24 + calendar_title_x, calendar_top), calendar_title_text, font = calendar_title_font, fill = 0)
        
        # Weekdays
        draw.text((24, 30 + calendar_top), 'Su', font = getFont(15, 'Bold'), fill = 0)
        draw.text((55, 30 + calendar_top), 'M', font = getFont(15, 'Bold'), fill = 0)
        draw.text((84, 30 + calendar_top), 'T', font = getFont(15, 'Bold'), fill = 0)
        draw.text((112, 30 + calendar_top), 'W', font = getFont(15, 'Bold'), fill = 0)
        draw.text((138, 30 + calendar_top), 'Th', font = getFont(15, 'Bold'), fill = 0)
        draw.text((170, 30 + calendar_top), 'F', font = getFont(15, 'Bold'), fill = 0)
        draw.text((198, 30 + calendar_top), 'S', font = getFont(15, 'Bold'), fill = 0)

        date_line_height = 0

        # Weeks
        for week in days_in_weeks:
            date_spacing = 0

            for day in week:

                if len(str(day)) == 1:
                    day_text = '  ' + str(day)
                else:
                    day_text = str(day)

                # Draw a cute lil box around today's date
                if day == today:
                    draw.rectangle((
                        20 + date_spacing,                   # x0
                        56 + calendar_top + date_line_height,     # y0
                        46 + date_spacing,                  # x1
                        76  + calendar_top + date_line_height),  # y1
                    fill = 0)
                    font_weight = 'Bold'
                    font_fill = 255
                else:
                    font_weight = 'Regular'
                    font_fill = 0

                if day == 0:
                    day_text = '  -'

                draw.text((24 + date_spacing, 56 + calendar_top + date_line_height), day_text, font = getFont(15, font_weight), fill = font_fill)
                date_spacing += 28
            
            date_line_height += 22
    
    def draw_date(self):
        print('draw date')

        # Center-alignment trickery
        date_font = getFont(148, 'Regular')
        date_text = datetime.datetime.now().strftime('%-d')
        date_text_w = date_font.getsize(date_text)[0]
        date_text_x = (190 / 2) - (date_text_w / 2)
        day_font = getFont(32, 'Regular')
        day_text = datetime.datetime.now().strftime('%A')
        day_text_w = day_font.getsize(day_text)[0]
        day_text_x = (190 / 2) - (day_text_w / 2)

        draw.text((24 + day_text_x, 12), day_text, font = day_font, fill = 0)
        draw.text((24 + date_text_x, 16), date_text, font = date_font, fill = 0)

    def draw_events(self):
        print('draw events')
        global events
        line_height = 16
        month_count = datetime.datetime.now().strftime('%B').upper()

        # Sort formatted events by date (closest -> furthest)
        dates_sort = [ datetime.datetime.strptime(event_key, '%Y-%m-%d') for event_key in events.keys() ]
        dates_sort.sort()
        dates_sort = [ datetime.datetime.strftime(date_key, '%Y-%m-%d') for date_key in dates_sort ]

        for date in dates_sort:
            # Event Group Date
            event_datetime = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            event_month = event_datetime.strftime('%B').upper()

            # If event is today
            if event_datetime == datetime.datetime.today().date():
                draw.text((260, line_height), 'TODAY', font = getFont(15, 'Regular'), fill = 0)   # Day

            else:
                # If event isn't this month
                if event_month != month_count:
                    month_count = event_month

                    draw.text((325, line_height), event_month, font = getFont(15, 'Regular'), fill = 0)   # Month
                    line_height += 32
                    
                # Draw date & day
                event_date_font = getFont(42, 'Regular')
                event_date_text = event_datetime.strftime('%d')
                event_day_font = getFont(15, 'Regular')
                event_day_text = event_datetime.strftime('%a').upper()
                event_day_text_w = event_day_font.getsize(event_day_text)[0]
                event_day_text_x = 42 - event_day_text_w

                draw.text((255, line_height - 10), event_date_text, font = event_date_font, fill = 0)   # Date
                draw.text((255 + event_day_text_x, 40 + line_height), event_day_text, font = event_day_font, fill = 0)   # Day

            for event in events[date]:
                event_summary = event['summary']

                # Event Location
                try:
                    event_location = '@ ' + event['location'].replace('\n', ', ')
                except:
                    event_location = ''

                # Time
                try:
                    event_datetime_start = datetime.datetime.strptime(event['start']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S')
                    event_datetime_end = datetime.datetime.strptime(event['end']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S')
                    event_time_start = event_datetime_start.strftime('%-I%p') if event_datetime_start.minute == 0 else event_datetime_start.strftime('%-I:%M%p')
                    event_time_end = event_datetime_end.strftime('%-I%p') if event_datetime_end.minute == 0 else event_datetime_end.strftime('%-I:%M%p')

                    # For multi-day events
                    if event['start']['dateTime'][0:10] == event['end']['dateTime'][0:10]:
                        event_time = '{} - {} '.format(event_time_start, event_time_end)     # "7:30AM - 10:45PM"

                    else:
                        event_time = ''

                except:
                    event_datetime_start = datetime.datetime.strptime(event['start']['date'], '%Y-%m-%d')
                    event_datetime_end = datetime.datetime.strptime(event['end']['date'], '%Y-%m-%d')
                    event_time = ''

                # Truncate long descriptions
                if len(event_summary) > 26:
                    event_summary = event_summary[0:26] + '...' 
                
                if len(event_location) > 26:
                    event_location = event_location[0:26] + '...' 
                
                # Draw summary & details
                draw.text((325, line_height), event_summary, font = getFont(15, 'Bold'), fill = 0)   # Summary
                line_height += 14

                if (event_time):
                    line_height += 10
                    draw.text((325, line_height), event_time, font = getFont(15, 'Regular'), fill = 0)  # Time
                    line_height += 10
                if (event_location):
                    line_height += 10
                    draw.text((325, line_height), event_location, font = getFont(15, 'Regular'), fill = 0)  # Location
                    # line_height += 10

                line_height += 12

                if line_height > EPD_HEIGHT:
                    break

            line_height += 32

            if line_height > EPD_HEIGHT:
                break

    def draw_weather(self):
        print('draw weather')
    
        temp_font = getFont(36, 'Regular')
        temp_text = weather['temperature']
        temp_text_w = temp_font.getsize(temp_text)[0]
        temp_text_x = 580 - temp_text_w

        with open('./weather_conditions.json') as f:
            weather_conditions = json.load(f)

        weather_font = ImageFont.truetype('/home/pi/python_programs/pi-cal/src/fonts/weather_icons/fonts/weather_icons.ttf', 36)
        weather_icon = weather_conditions[str(weather['weather'])]['icon']
        weather_icon_w = weather_font.getsize(weather_icon)[0]
        weather_icon_x = 624 - weather_icon_w

        draw.text((temp_text_x, 16), temp_text, font = temp_font, fill = 0)   # Temperature
        draw.text((weather_icon_x, 18), weather_icon, font = weather_font, fill = 0)     # Weather icon

def render():
    # Render
    draw.multiline_text((560, 64), 'Updated \n {} \n {}'.format(datetime.datetime.now().strftime('%Y/%m/%d'), datetime.datetime.now().strftime('%H:%M')), align = 'right', font = getFont(12, 'Regular'))
    epd.display_frame(epd.get_frame_buffer(image))

if __name__ == '__main__':
    main()
