from unittest import IsolatedAsyncioTestCase

from aiohttp import ClientSession

import webparser


class TestWebParser(IsolatedAsyncioTestCase):

    async def test_get_machines_status(self):
        async with ClientSession() as session:
            try:
                for machine_status in await webparser.get_machines_status(session):
                    print(machine_status)
            except ConnectionError:
                pass

    async def test_get_time_last_update(self):
        async with ClientSession() as session:
            try:
                print(await webparser.get_time_last_update(session))
            except ConnectionError:
                pass

    async def test_get_machines(self):
        async with ClientSession() as session:
            try:
                for machine in await webparser.get_machines(session):
                    print(machine)
            except ConnectionError:
                pass
