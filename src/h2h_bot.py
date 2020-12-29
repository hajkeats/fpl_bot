#!/usr/bin/env python3

from os import environ
import datetime
import requests
from prettytable import PrettyTable
from dateutil.parser import parse
import boto3
from botocore.exceptions import ClientError


# URLS
API_BASE = 'https://fantasy.premierleague.com/api'
GENERAL_INFO = f'{API_BASE}/bootstrap-static/'
H2H_LEAGUE_MATCHES = f'{API_BASE}/leagues-h2h-matches/league/{environ["LEAGUE_ID"]}/'
H2H_LEAGUE_STANDINGS = f'{API_BASE}/leagues-h2h/{environ["LEAGUE_ID"]}/standings'


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

    print('The results of this weeks fantasy games are here!')
    for f in fixtures:
        total_1 = f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} ({f["entry_1_points"]} points)'
        total_2 = f'{f["entry_2_player_name"]}\'s {f["entry_2_name"]} ({f["entry_2_points"]} points)'
        if f['entry_1_points'] > f['entry_2_points']:
            print(f'{total_1} won against {total_2}.')
        elif f['entry_2_points'] > f['entry_1_points']:
            print(f'{total_2} won against {total_1}.')
        else:
            print(f'{total_1} drew with {total_2}.')


def report_table():
    """
    Reports the table for a h2h league as it stands
    """
    league_name, standings = get_league_table()
    print(league_name + ' table')

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
    print(table)


def report_fixtures(event_id):
    """
    Reports fixtures for an upcoming gameweek
    :param event_id: the id of the coming gameweek
    """
    fixtures = get_gameweek_fixtures(event_id)

    print('In this coming gameweek we have some tasty fixtures:')
    for f in fixtures:
        print(f'{f["entry_1_player_name"]}\'s {f["entry_1_name"]} play {f["entry_2_player_name"]}\'s '
              f'{f["entry_2_name"]}')


def between_gameweeks(event_id, deadline_time):
    """
    State 4: In between gameweeks. Checks deadline against current date.
    Reports next fixtures if day of the deadline
    :param event_id:
    :param deadline_time:
    """
    today = datetime.datetime.today()
    deadline = parse(deadline_time)
    if deadline.date() == today.date():
        # New Gameweek Starting
        print(f'The deadline for the coming fantasy gameweek is today at {deadline.time()}')
        report_fixtures(event_id)


def main():
    """
    Possible states

    State 1: Newly launched lambda. No working id.
        a: If current event, set working id = current event id then consider State 4.
        b: If no current event, season not in progress. Consider State 2.
    State 2: No current event. Season not in progress. Exit.
    State 3: Working id == previous event id. Gameweek is finished. Report results.
    State 4: Working id == current event id. In between gameweeks. Report fixtures if on day of deadline.
    """
    current_event, previous_event = get_current_events()
    dynamo_db = boto3.client('dynamodb')

    try:
        working_id = dynamo_db.get_item(TableName='GameweekIDs', Key='working_id')
    except ClientError:
        working_id = None

    if not working_id:
        # State 1 - Newly deployed lambda
        if current_event:
            # a: Season in progress -> State 4
            dynamo_db.put_item(TableName='GameweekIDs', Item={'working_id': {'N': current_event['id']}})
            between_gameweeks(current_event['id'], current_event['deadline_time'])
            return
        else:
            # b: Season has finished -> State 2
            return

    if not current_event:
        # State 2 - Season has just finished
        return

    if working_id == previous_event['id']:
        # State 3 - Gameweek Finished
        dynamo_db.put_item(TableName='GameweekIDs', Item={'working_id': {'N': current_event['id']}})
        report_results(previous_event['id'])
        report_table()
        return
    elif working_id == current_event['id']:
        # State 4 - Between gameweeks
        between_gameweeks(current_event['id'], current_event['deadline_time'])
        return
    else:
        # Unknown state. Debug and exit
        print(f'Unknown state reached. working_id={working_id}, current_event={current_event["id"]}')
        return


if __name__ == "__main__":
    main()
