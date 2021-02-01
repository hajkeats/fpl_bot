from os import environ
from fpl import FPL
import aiohttp
import asyncio


def run_sync(func):
    """
    Call an asynchronous function from a synchronous one.
    :param func: The asynchronous function to be called
    """
    def sync_wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(func(*args, **kwargs))
    return sync_wrapper


@run_sync
async def get_current_gameweeks():
    """
    Returns the current + previous gameweeks
    :return: current gameweek + previous gameweek
    """
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        await fpl.login(email=environ['FPL_EMAIL'], password=environ['FPL_PASSWORD'])
        previous_gameweek = None
        for i in range(1, 38):
            current_gameweek = await fpl.get_gameweek(i)
            if not current_gameweek.finished:
                return current_gameweek, previous_gameweek
            previous_gameweek = current_gameweek
        return None, previous_gameweek


@run_sync
async def get_final_gameweek_fixture_date(gameweek_id):
    """
    Gets the date of the final fixture of a gameweek.
    :param gameweek_id: The id of a gameweek
    :return: the date of the last fixture
    """
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        await fpl.login(email=environ['FPL_EMAIL'], password=environ['FPL_PASSWORD'])
        fixtures = await fpl.get_fixtures_by_gameweek(gameweek=gameweek_id)
        return fixtures[-1].kickoff_time


@run_sync
async def get_gameweek_fixtures(gameweek_id):
    """
    Returns the fixtures for a given league and gameweek
    :param gameweek_id: the identifier for the gameweek to get fixtures for
    :return: fixtures for the gameweek
    """
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        await fpl.login(email=environ['FPL_EMAIL'], password=environ['FPL_PASSWORD'])
        h2h_league = await fpl.get_h2h_league(environ['LEAGUE_ID'])
        return await h2h_league.get_fixtures(gameweek=gameweek_id)
