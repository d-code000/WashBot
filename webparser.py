import re
import logging
from typing import Sequence

from bs4 import BeautifulSoup
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError, ClientConnectorError, ClientResponseError


import config
from database import Machine


_MachineStatus = dict[int: str]
_TimeLastUpdate = tuple[str, ...]

logger = logging.getLogger(__name__)


async def _get_site_soup(session: ClientSession) -> BeautifulSoup:
    try:
        async with session.get(config.SITE_URL) as response:
            try:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), "lxml")
                logger.info(f"Request to site {config.SITE_URL}")
                return soup
            except ClientResponseError as exc:
                msg = f"HTTP error, status code {response.status}"
                logger.error(msg)
                raise ConnectionError(msg) from exc
    except ClientConnectorError as exc:
        msg = "Connection error"
        logger.error(msg)
        raise ConnectionError(msg) from exc
    except ClientError:
        logger.error("Other requests exceptions", exc_info=True)


async def get_machines_status(session: ClientSession) -> _MachineStatus:
    site_soup = await _get_site_soup(session)
    machines_status = {}
    try:
        machines = site_soup.find_all("div", class_=re.compile(r"col mb-3 childItem child.*"))
        for machine in machines:
            num = int(machine.find("div", class_="text-center").text)
            status = re.search(
                r"[^ ].*[^ ]",
                machine.find_all("div", class_="text-center")[1].text.replace("\n", "")
                ).group()
            machines_status.update({num: status})
        return machines_status
    except AttributeError:
        logger.error("Search machine status: some information has not been found, "
                     "a change in the search algorithm is required")
        return ()


async def get_time_last_update(session: ClientSession) -> _TimeLastUpdate:
    site_soup = await _get_site_soup(session)
    try:
        time_last_update = site_soup.find("div", attrs={"data-toggle": "tooltip"}).text
        date = re.search(r"\d\d\.\d\d\.\d{4}", time_last_update).group()
        time = re.search(r"\d\d:\d\d", time_last_update).group()
        return tuple([date, time])
    except AttributeError:
        logger.error("Search time last update: some information has not been found, "
                     "a change in the search algorithm is required")
        return tuple()


async def get_machines(session: ClientSession) -> Sequence[Machine]:
    site_soup = await _get_site_soup(session)
    result = []
    try:
        machines = site_soup.find_all("div", class_=re.compile(r"col mb-3 childItem child.*"))
        for machine in machines:
            num = int(machine.find("div", class_="text-center").text)
            kind = machine.div["title"]
            prise = machine.find("span", class_=re.compile(r"pl-1 pr-1 withTooltip.*")).text
            prise = int(re.search(r"\d+", prise).group())
            result.append(Machine(
                seq_num=num,
                type=kind,
                prise=prise
            ))
        return tuple(result)
    except AttributeError:
        logger.error("Search machines: some information has not been found, "
                     "a change in the search algorithm is required")
        return ()
