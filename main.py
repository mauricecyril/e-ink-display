# main

# TODO:
# - event['start']['dateTime'] & event['end']['dateTime'] may span a few days
# - On multi-day event, if date is start day, display "Starts @ 7:30AM"
# - On multi-day event, if date is end day, display "Ends @ 10:30PM"
# - Show "Today" & populate accordingly
# - Show "X more events this week"

import calendar
import epd7in5
import datetime
# from googleapiclient.discovery import build
# from httplib2 import Http
import json
# from oauth2client import file, client, tools
# import os
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from pprint import pprint
# import sys

with open('data.json') as f:
    events = json.load(f)

# print(os.getcwd())
# print(sys.platform)

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
EPD_WIDTH = 640
EPD_HEIGHT = 384

def main():
    fetchEvents()
    # drawEvents()

def fetchEvents():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('e-ink_home_display-dcb881b9fb01.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    
    print('Getting the upcoming 10 events')
    
    events_result = service.events().list(
        calendarId='lkopeh0sr1m9svqcggd0pms2ug@group.calendar.google.com',
        maxResults=10,
        orderBy='startTime',
        singleEvents=True,
        timeMin=now
    ).execute()
    
    global events
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    
    for event in events: 
        start = event['start'].get('dateTime', event['start'].get('date'))

def formatEvents(events):
    print('formatEvents')

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

    # pprint(events_format)
    return events_format

def draw():
    print('drawEvents')
    
    # Initialize E-Paper Display inferface
    epd = epd7in5.EPD()
    epd.init()
    

    # For simplicity, the arguments are explicit numerical coordinates
    image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)    # 1: clear the frame
    draw = ImageDraw.Draw(image)

    # Fonts
    def font(size, weight):
        return ImageFont.truetype('/home/pi/python_programs/pi-cal/fonts/OpenSans-{}.ttf'.format(weight), size)
    

    def drawCalendar():
        print('drawEvents')

        now = datetime.datetime.now()
        today = now.day
        year = now.year
        month = now.month
        month_str = now.strftime('%B')
        calendar_top = 200


        # calendar.setfirstweekday(calendar.SUNDAY)
        cal = calendar.Calendar(calendar.SUNDAY)
        days_in_weeks = cal.monthdayscalendar(year, month)

        # Title
        draw.text((24, calendar_top), '{} {}'.format(month_str, year), font = font(20, 'Regular'), fill = 0)
        
        # Weekdays
        draw.text((24, 30 + calendar_top), 'Su', font = font(18, 'Bold'), fill = 0)
        draw.text((56, 30 + calendar_top), 'M', font = font(18, 'Bold'), fill = 0)
        draw.text((82, 30 + calendar_top), 'T', font = font(18, 'Bold'), fill = 0)
        draw.text((112, 30 + calendar_top), 'W', font = font(18, 'Bold'), fill = 0)
        draw.text((138, 30 + calendar_top), 'Th', font = font(18, 'Bold'), fill = 0)
        draw.text((168, 30 + calendar_top), 'F', font = font(18, 'Bold'), fill = 0)
        draw.text((194, 30 + calendar_top), 'S', font = font(18, 'Bold'), fill = 0)

        date_height = 0

        # Weeks
        for week in days_in_weeks:
            date_spacing = 0

            for day in week:
                day_text = day

                if day == today:
                    draw.rectangle((
                        20 + date_spacing,                   # x0
                        56 + calendar_top + date_height,     # y0
                        44 + date_spacing,                  # x1
                        76  + calendar_top + date_height),  # y1
                    fill = 0)
                    font_weight = 'Bold'
                    font_fill = 255
                else:
                    font_weight = 'Regular'
                    font_fill = 0

                if day == 0:
                    day_text = '-'
                
                draw.text((24 + date_spacing, 56 + calendar_top + date_height), str(day_text), font = font(15, font_weight), fill = font_fill)
                date_spacing += 28
            
            date_height += 22
    
    def drawDate():
        print('drawDate')
        day = datetime.datetime.now().strftime('%A')
        date = datetime.datetime.now().strftime('%-d')

        draw.text((28, 8), day, font = font(32, 'Regular'), fill = 0)
        draw.text((29, 8), date, font = font(148, 'Regular'), fill = 0)

    def drawEvents():
        print('drawEvents')
        line_height = 4

        # Render "Today"
        draw.text((260, 16), 'TODAY', font = font(15, 'Regular'), fill = 0)   # Day
        draw.text((325, 16), 'Not much going on!', font = font(15, 'Italic'), fill = 0)  # Details

        events_format = formatEvents(events)

        # Sort formatted events by date
        dates_sort = [ datetime.datetime.strptime(event_key, '%Y-%m-%d') for event_key in events_format.keys() ]
        dates_sort.sort()
        dates_sort = [ datetime.datetime.strftime(date_key, '%Y-%m-%d') for date_key in dates_sort ]

        for date in dates_sort:
            # Event Group Date
            event_datetime = datetime.datetime.strptime(date, '%Y-%m-%d')
            event_date = event_datetime.strftime('%d')
            event_day = event_datetime.strftime('%a').upper()

            # If event isn't this week or month
            event_week = event_datetime.strftime('%U')
            event_month = event_datetime.strftime('%b').upper()

            if event_week != datetime.datetime.now().strftime('%U'):
                week_day = int(event_datetime.strftime('%w'))
                week_of = 6 - week_day

                draw.text((325, 48 + line_height), event_month, font = font(15, 'Regular'), fill = 0)   # Month
                line_height += 16

            # Draw date & day
            draw.text((255, 48 + line_height), event_date, font = font(42, 'Regular'), fill = 0)   # Date
            draw.text((260, 100 + line_height), event_day, font = font(15, 'Regular'), fill = 0)   # Day

            for event in events_format[date]:
                # print(event['summary'])
                event_summary = event['summary']

                # Event Location
                try:
                    event_location = '@ ' + event['location']
                except:
                    event_location = ''

                # Time
                try:
                    # print('try')
                    event_datetime_start = datetime.datetime.strptime(event['start']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S')
                    event_datetime_end = datetime.datetime.strptime(event['end']['dateTime'][0:19], '%Y-%m-%dT%H:%M:%S')
                    event_time_start = event_datetime_start.strftime('%-I') + ':' + event_datetime_start.strftime('%M') + event_datetime_start.strftime('%p')       # "7:30AM'
                    event_time_end = event_datetime_end.strftime('%-I') + ':' + event_datetime_end.strftime('%M') + event_datetime_end.strftime('%p')     # "10:30PM"

                    # For multi-day events
                    if event['start']['dateTime'][0:10] == event['end']['dateTime'][0:10]:
                        # print('Same day')
                        event_time = '{} - {} '.format(event_time_start, event_time_end)     # "7:30AM - 10:45PM"

                    else :
                        # print('Different days')
                        event_time = ''

                except:
                    # print('except')
                    event_datetime_start = datetime.datetime.strptime(event['start']['date'], '%Y-%m-%d')
                    event_datetime_end = datetime.datetime.strptime(event['end']['date'], '%Y-%m-%d')
                    event_time = ''

                # Truncate long descriptions
                if len(event_summary) > 24:
                    event_summary = event_summary[0:24] + '...' 
                
                if len(event_location) > 20:
                    event_location = event_location[0:20] + '...' 
                
                # Draw summary & details
                draw.text((325, 60 + line_height), event_summary, font = font(15, 'Bold'), fill = 0)   # Summary
                draw.text((325, 82 + line_height), event_time + event_location, font = font(15, 'Regular'), fill = 0)  # Details

                line_height += 32

            line_height += 48

    drawCalendar()
    drawDate()
    drawEvents()

    # Render
    epd.display_frame(epd.get_frame_buffer(image))

if __name__ == '__main__':
    draw()
