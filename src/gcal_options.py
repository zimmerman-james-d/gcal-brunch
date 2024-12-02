'''
Python Script for finding meeting times for shared google calendars.
See README.md for setup instructions.
'''
import json
import os
import datetime
import zoneinfo

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

#PATHS
CRED_PATH = os.path.join('configuration', 'credentials.json')
TOKEN_PATH = os.path.join('configuration', 'token.json')
EMOJI_PATH = os.path.join('configuration', 'emoji.json')
PREFS_PATH = os.path.join('configuration', 'preferences.json')
with open(EMOJI_PATH, 'r', encoding='utf-8') as emoji_file:
    EMOJI_OPTIONS = json.load(emoji_file)
with open(PREFS_PATH, 'r', encoding='utf-8') as prefs_file:
    PREF_OPTIONS = json.load(prefs_file)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
START_OF_DAY = PREF_OPTIONS['EarliestStart']
END_OF_DAY = PREF_OPTIONS['LatestEnd']
MEETING_WINDOW = PREF_OPTIONS['LengthOfMeetingWindow']
WEEKEND_DAYS_AS_INT = [5, 6]
ATTENDEES = [None]
EARLIEST_MEETING_TIME = datetime.datetime(2024, 12, 3, tzinfo=datetime.timezone.utc)


def api_queries(time_min: datetime.datetime,
                time_max: datetime.datetime) -> tuple[list, list]:
    '''
    Queries Google Calendar APIs for attendee meeting availabiity. Returns a tuple of user time zones, and their availability.
    '''
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh_handler(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding='utf-8') as token:
            token.write(creds.to_json())

    try:
        time_zones = []
        service = build('calendar', 'v3', credentials=creds)
        free_busy = service.freebusy().query(
            body={
                'timeMin': time_min.isoformat(),
                'timeMax': time_max.isoformat(),
                'items': construct_user_list(ATTENDEES)
            }).execute()
        for attendee in ATTENDEES:
            calendar_object = service.calendars().get(
                calendarId=attendee).execute()
            time_zones.append(calendar_object['timeZone'])
        time_zones = list(set(time_zones))

    except HttpError as err:
        print(err)
    return free_busy['calendars'], time_zones


def sort_time_zones(time_zone_list: list) -> list:
    '''
    Sorts time zones of attendees to normalize display of meeting times from latest
    local time to earliest local time.
    '''
    temp_holder = {}
    out_list = []
    for time_zone in time_zone_list:
        temp_holder[datetime.datetime.now(
            zoneinfo.ZoneInfo(time_zone)).strftime('%z')] = time_zone
    for time_key_value_pair in sorted(temp_holder.items()):
        out_list.append(time_key_value_pair[1])
    return out_list


def prune_weekends(meeting_times: list) -> list:
    '''
    Filters availability to only include weekdays.
    '''
    valid_times = []
    for meeting_time in meeting_times:
        if meeting_time.weekday() not in WEEKEND_DAYS_AS_INT:
            valid_times.append(meeting_time)
    return valid_times


def construct_user_list(attendees: list) -> list:
    '''
    Converts list of atendees into dict expected by Google Calendar API.
    '''
    calendar_list = []
    for attendee in attendees:
        calendar_list.append({'id': attendee})
    return calendar_list


def get_availability(busy_times: list[dict]) -> list[dict]:
    '''
    Merges the busy times for all attendees into one list.
    '''
    merged_busy = []
    for calendar in busy_times:
        merged_busy += busy_times[calendar]['busy']
    return merged_busy


def round_to_half_hour(meeting_time: datetime.datetime) -> datetime.datetime:
    '''
    If a meeting time is invalid, rolls next meeting to the top or bottom of the hour.
    '''
    if meeting_time.minute not in (0, 30):
        if meeting_time.minute < 30:
            meeting_time = meeting_time.replace(minute=30)
        else:
            meeting_time = meeting_time.replace(minute=0)
            meeting_time = meeting_time + datetime.timedelta(hours=1)
    return meeting_time


def string_to_datetime(time_string: str) -> datetime.datetime:
    '''
    Wrapper around strptime
    '''
    return datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S%z")


def find_a_time(availaibity: list[dict],
                start_time: datetime.datetime,
                end_time: datetime.datetime,
                earliest_start: datetime.datetime,
                latest_finish: datetime.datetime,
                interval: int = 30,
                duration: int = 45):
    '''
    Finds times where all attendees are avaialbe within the window.
    '''
    meeting_times = []
    meeting_start_time = start_time
    meeting_start_time = meeting_start_time.replace(minute=0,
                                                    second=0,
                                                    microsecond=0)
    meeting_end_time = start_time + datetime.timedelta(minutes=duration)
    while meeting_end_time < end_time:
        meeting_start_time = round_to_half_hour(meeting_start_time)
        if meeting_start_time.hour < earliest_start.hour:
            meeting_start_time = meeting_start_time.replace(
                hour=earliest_start.hour)
            meeting_end_time = meeting_start_time + datetime.timedelta(
                minutes=duration)
        elif meeting_end_time.hour >= latest_finish.hour or meeting_end_time.day != meeting_start_time.day:
            meeting_start_time = meeting_start_time + datetime.timedelta(
                days=1)
            meeting_start_time = meeting_start_time.replace(
                hour=earliest_start.hour)
            meeting_end_time = meeting_start_time + datetime.timedelta(
                minutes=duration)
        slot_available = True
        for blocked in availaibity:
            if string_to_datetime(blocked['start']
                                  ) <= meeting_start_time < string_to_datetime(
                                      blocked['end']):
                slot_available = False
                meeting_start_time = string_to_datetime(blocked['end'])
                meeting_start_time = round_to_half_hour(meeting_start_time)
                continue
            if string_to_datetime(
                    blocked['start']) <= meeting_end_time < string_to_datetime(
                        blocked['end']):
                slot_available = False
                meeting_start_time = string_to_datetime(blocked['end'])
                meeting_start_time = round_to_half_hour(meeting_start_time)
                continue
        if slot_available and meeting_start_time < end_time:
            meeting_times.append(meeting_start_time)
            meeting_start_time = meeting_start_time + datetime.timedelta(
                minutes=interval)
        meeting_end_time = meeting_start_time + datetime.timedelta(
            minutes=duration)
    return meeting_times


def get_min_max_start(
        time_zones: list[str]) -> tuple[datetime.datetime, datetime.datetime]:
    '''
    Gets the earliest and latest meeting times based on the time zones of the attendees.
    '''
    start_times = []
    end_times = []
    for time_zone in time_zones:
        start_times.append(
            datetime.datetime(2024,
                              5,
                              20,
                              START_OF_DAY,
                              tzinfo=zoneinfo.ZoneInfo(time_zone)))
        end_times.append(
            datetime.datetime(2024,
                              5,
                              20,
                              END_OF_DAY,
                              tzinfo=zoneinfo.ZoneInfo(time_zone)))
    return max(start_times), min(end_times)


def main() -> None:
    '''
    Handles construction of the meeting scheduling message.
    '''
    print(
        "An automated script was used to generate a list of potential meeting times.",
        "Here's a list of emoji to select times that work for you!")
    start_time = EARLIEST_MEETING_TIME
    end_time = start_time + datetime.timedelta(days=MEETING_WINDOW)
    busy_times, time_zones = api_queries(start_time, end_time)
    early_start, late_end = get_min_max_start(time_zones)
    time_zones = sort_time_zones(time_zones)
    meeting_times = find_a_time(get_availability(busy_times), start_time,
                                end_time,
                                early_start.astimezone(datetime.timezone.utc),
                                late_end.astimezone(datetime.timezone.utc))
    meeting_times = prune_weekends(meeting_times)
    for i, meeting_time in enumerate(meeting_times):
        current_time = meeting_time
        time_string = ""
        for time_zone in time_zones:
            time_string += f" {current_time.astimezone(zoneinfo.ZoneInfo(time_zone)).strftime('%I:%M%p %Z')}"
        print(
            f":{EMOJI_OPTIONS[(int(i))]}: {current_time.strftime('%a, %b %d')}:{time_string}"
        )
    if PREF_OPTIONS["IncludeNoAsOption"]:
        print(
            f"{PREF_OPTIONS['NoEmoji']} I'm extremely busy and won't be able to make it."
        )


if __name__ == "__main__":
    main()
