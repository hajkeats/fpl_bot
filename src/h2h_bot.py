#!/usr/bin/env python3

from os import environ
import datetime
import re
import requests
from prettytable import PrettyTable
from dateutil.parser import parse
from fbchat import Client
from fbchat.models import Message, ThreadType
import fbchat


# HACKY STUFF - fbchat is unmaintained and has issues. These lines comes from the repo issue #615
fbchat._util.USER_AGENTS    = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36"
]
fbchat._state.FB_DTSG_REGEX = re.compile(r'"name":"fb_dtsg","value":"(.*?)"')

# URLS
API_BASE = 'https://fantasy.premierleague.com/api'
GENERAL_INFO = f'{API_BASE}/bootstrap-static/'
PREM_MATCHES = f'{API_BASE}/fixtures/'
H2H_LEAGUE_MATCHES = f'{API_BASE}/leagues-h2h-matches/league/{environ["LEAGUE_ID"]}/'
H2H_LEAGUE_STANDINGS = f'{API_BASE}/leagues-h2h/{environ["LEAGUE_ID"]}/standings'

fb_client = Client(environ['FB_EMAIL'], environ['FB_PASSWORD'])


def send(message):
    """
    Uses the facebook client to send a message to the group chat
    """
    print("Sending:", message)
    fb_client.send(Message(text=message), thread_id=environ['THREAD_ID'], thread_type=ThreadType.USER)


def get_current_events():
    """
    Returns details for both the most recently finished gameweek and the next coming gameweek
    :return: current_event details, previous_event details
    """
    events = requests.get(GENERAL_INFO).json()['events']
    previous_event = None
    for event in events:
        if not event['finished']:
            return event, previous_event
        previous_event = event


def get_final_gameweek_fixture_date(event_id):
    """
    Gets the date of the final fixture of the most recent gameweek.
    :param event_id: The id of the previously finished gameweek
    """
    fixtures = requests.get(PREM_MATCHES).json()
    fixture_dates = [f['kickoff_time'] for f in fixtures if f['event'] == event_id]
    return fixture_dates[-1]


def get_league_table():
    """
    Returns the table for a given league
    :return: the league name and the current standings
    """
    h2h_standings = requests.get(H2H_LEAGUE_STANDINGS).json()
    return h2h_standings['league']['name'], h2h_standings['standings']['results']


def get_gameweek_fixtures(event_id):
    """
    Returns the fixtures for a given league and gameweek
    :param event_id: the identifier for the gameweek to get fixtures for
    :return: fixtures for the gameweek
    """
    h2h_fixtures = requests.get(H2H_LEAGUE_MATCHES).json()
    return [f for f in h2h_fixtures['results'] if f['event'] == event_id]


def report_results(event_id):
    """
    Reports results for a finished gameweek
    :param event_id: the id for the results
    """
    fixtures = get_gameweek_fixtures(event_id)

    send('The results of this weeks fantasy games are here!')
    for f in fixtures:
        total_1 = f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} ({f["entry_1_points"]} points)'
        total_2 = f'{f["entry_2_player_name"]}\'s {f["entry_2_name"]} ({f["entry_2_points"]} points)'
        if f['entry_1_points'] > f['entry_2_points']:
            send(f'{total_1} won against {total_2}.')
        elif f['entry_2_points'] > f['entry_1_points']:
            send(f'{total_2} won against {total_1}.')
        else:
            send(f'{total_1} drew with {total_2}.')


def report_table():
    """
    Reports the table for a h2h league as it stands
    """
    league_name, standings = get_league_table()
    send(league_name + ' table')

    table = PrettyTable(['Rank', 'Team', 'Manager', 'Won', 'Drawn', 'Lost'])
    for team in standings:
        table.add_row([
            team['rank'],
            team['entry_name'],
            team['player_name'],
            team['matches_won'],
            team['matches_drawn'],
            team['matches_lost']
        ])
    send(str(table))


def report_fixtures(event_id):
    """
    Reports fixtures for an upcoming gameweek
    :param event_id: the id of the coming gameweek
    """
    fixtures = get_gameweek_fixtures(event_id)

    send('In this coming gameweek we have some tasty fixtures:')
    for f in fixtures:
        send(f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} play {f["entry_2_player_name"]}\'s '
              f'{f["entry_2_name"]}')


def bot_handler(event, context):
    """
    Lambda handler function
    Reports on fixtures or results from a given league depending on the date.
    """
    current_event, previous_event = get_current_events()

    # All events considered 'finished' - Season is not in progress
    if not current_event:
        return

    current_event_deadline = parse(current_event['deadline_time'])
    last_match = parse(get_final_gameweek_fixture_date(previous_event['id']))
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(days=1)

    # If a gameweek finished yesterday
    if last_match.date() == yesterday.date():
        report_results(previous_event['id'])
        report_table()

    # If today is the start of a new gameweek
    if current_event_deadline.date() == today.date():
        send(f'The deadline for the coming fantasy gameweek is today at {current_event_deadline.time()}')
        report_fixtures(current_event['id'])
