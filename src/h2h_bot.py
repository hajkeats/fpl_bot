#!/usr/bin/env python3

from os import environ
import datetime
import re
from dateutil.parser import parse
import fbchat
from fbchat.models import Message, ThreadType
from src.fpl_funcs import get_gameweek_fixtures, get_current_gameweeks, get_final_gameweek_fixture_date

# HACKY STUFF - fbchat is unmaintained and has issues. These lines come from the repo issue #615
fbchat._util.USER_AGENTS = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/86.0.4240.75 Safari/537.36"]
fbchat._state.FB_DTSG_REGEX = re.compile(r'"name":"fb_dtsg","value":"(.*?)"')

# URLS
CHANGE_TEAM = 'https://fantasy.premierleague.com/my-team'
H2H_LEAGUE_STANDINGS = f'https://fantasy.premierleague.com/leagues/{environ["LEAGUE_ID"]}/standings/h'

fb_client = fbchat.Client(environ['FB_EMAIL'], environ['FB_PASSWORD'])


def send(message):
    """
    Uses the facebook client to send a message to the group chat
    :param message: the message to send
    """
    print("Sending:", message)
    fb_client.send(Message(text=message), thread_id=environ['THREAD_ID'], thread_type=ThreadType.GROUP)


def report_results(gameweek_id):
    """
    Reports results for a finished gameweek
    :param gameweek_id: the id for the results
    """
    fixtures = get_gameweek_fixtures(gameweek_id)

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

    send(f'The table has been updated: {H2H_LEAGUE_STANDINGS}')


def report_fixtures(gameweek_id):
    """
    Reports fixtures for an upcoming gameweek
    :param gameweek_id: the id of the coming gameweek
    """
    fixtures = get_gameweek_fixtures(gameweek_id)

    send('In this coming gameweek we have some tasty fixtures:')
    for f in fixtures:
        send(f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} play {f["entry_2_player_name"]}\'s '
             f'{f["entry_2_name"]}')


def bot_handler(event, context):
    """
    Lambda handler function
    Reports on fixtures or results from a given league depending on the date.
    """
    current_gameweek, previous_gameweek = get_current_gameweeks()
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(days=1)

    # At least one gameweek completed
    if previous_gameweek:
        last_match = parse(get_final_gameweek_fixture_date(previous_gameweek.id))
        # If a gameweek finished yesterday
        print("Gameweek Last Match: ", last_match.date(), "Yesterday:", yesterday.date())
        if last_match.date() == yesterday.date():
            print("Reporting Results!")
            report_results(previous_gameweek.id)

    # At least one gameweek to come/in progress
    if current_gameweek:
        current_gameweek_deadline = parse(current_gameweek.deadline_time)
        # If today is the start of the gameweek
        print("Gameweek Deadline: ", current_gameweek_deadline.date(), "Today:", today.date())
        if current_gameweek_deadline.date() == today.date():
            print("Reporting Fixtures!")
            send(f'The deadline for the coming fantasy gameweek is today at {current_gameweek_deadline.time()}')
            send(f'Change your team here: {CHANGE_TEAM}')
            report_fixtures(current_gameweek.id)
