#!/usr/bin/env python3

from os import environ
import datetime
import re
from dateutil.parser import parse
import boto3
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


def get_previous_session(table):
    """
    Returns the previous session from dynamodb table
    :param table: the table to get session from
    :return Latest session cookies
    """
    resp = table.get_item(Key={'Name': 'session_cookies'})
    try:
        return resp['Item']['Session']
    except KeyError:
        return None


def store_current_session(table, session):
    """
    Stores the session in a dynamodb table
    :param table: The table in which to store the session
    :param session: The session cookies for the current session
    """
    table.put_item(Item={
        'Name': 'session_cookies',
        'Session': session
    })


def send(message, fb):
    """
    Uses the facebook client to send a message to the group chat
    :param message: the message to send
    :param fb: the client used to send the msg
    """
    print("Sending:", message)
    fb.send(Message(text=message), thread_id=environ['THREAD_ID'], thread_type=ThreadType.GROUP)


def report_results(gameweek_id, fb):
    """
    Reports results for a finished gameweek
    :param gameweek_id: the id for the results
    :param fb: the client used to send the msg
    """
    fixtures = get_gameweek_fixtures(gameweek_id)

    send('The results of this weeks fantasy games are here!', fb)
    for f in fixtures:
        total_1 = f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} ({f["entry_1_points"]} points)'
        total_2 = f'{f["entry_2_player_name"]}\'s {f["entry_2_name"]} ({f["entry_2_points"]} points)'
        if f['entry_1_points'] > f['entry_2_points']:
            send(f'{total_1} won against {total_2}.', fb)
        elif f['entry_2_points'] > f['entry_1_points']:
            send(f'{total_2} won against {total_1}.', fb)
        else:
            send(f'{total_1} drew with {total_2}.', fb)

    send(f'The table has been updated: {H2H_LEAGUE_STANDINGS}', fb)


def report_fixtures(gameweek_id, fb):
    """
    Reports fixtures for an upcoming gameweek
    :param gameweek_id: the id of the coming gameweek
    :param fb: the client used to send the msg
    """
    fixtures = get_gameweek_fixtures(gameweek_id)

    send('In this coming gameweek we have some tasty fixtures:', fb)
    for f in fixtures:
        send(f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} play {f["entry_2_player_name"]}\'s '
             f'{f["entry_2_name"]}', fb)


def bot_handler(event, context):
    """
    Lambda handler function
    Reports on fixtures or results from a given league depending on the date.
    """
    table = boto3.resource('dynamodb').Table(environ['DYNAMO_TABLE'])
    previous_session = get_previous_session(table)
    fb = fbchat.Client(environ['FB_EMAIL'], environ['FB_PASSWORD'], session_cookies=previous_session)
    store_current_session(table, fb.getSession())

    current_gameweek, previous_gameweek = get_current_gameweeks()
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(days=1)

    # At least one gameweek completed
    if previous_gameweek:
        last_match = parse(get_final_gameweek_fixture_date(previous_gameweek.id))
        # If a gameweek finished yesterday
        print("Previous Gameweek Last Match: ", last_match.date(), "Yesterday:", yesterday.date())
        if last_match.date() == yesterday.date():
            report_results(previous_gameweek.id, fb)

    # At least one gameweek to come/in progress
    if current_gameweek:
        current_gameweek_deadline = parse(current_gameweek.deadline_time)
        # If today is the start of the gameweek
        print("Current Gameweek Deadline: ", current_gameweek_deadline.date(), "Today:", today.date())
        if current_gameweek_deadline.date() == today.date():
            send(f'The deadline for the coming fantasy gameweek is today at {current_gameweek_deadline.time()}', fb)
            send(f'Change your team here: {CHANGE_TEAM}', fb)
            report_fixtures(current_gameweek.id, fb)
        else:
            # Its finished but not reported finished
            last_match = parse(get_final_gameweek_fixture_date(current_gameweek.id))
            print("Current Gameweek Last Match: ", last_match.date(), "Yesterday:", yesterday.date())
            if last_match.date() == yesterday.date():
                report_results(current_gameweek.id, fb)
