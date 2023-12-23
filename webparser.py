import re
import logging
from typing import Union, Sequence

import requests
from bs4 import BeautifulSoup


import config
from service import cache
from database import Machines


_MachineStatus = dict[int: str]
_TimeLastUpdate = tuple[str, ...]

logger = logging.getLogger(__name__)


async def _get_site_soup() -> BeautifulSoup:
    try:
        r = requests.get(config.SITE_URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        logger.info(f"Request to site {config.SITE_URL}")
        return soup
    except requests.exceptions.HTTPError as exc:
        msg = f"HTTP error, status code {r.status_code}"
        logger.error(msg)
        raise ConnectionError(msg) from exc
    except requests.exceptions.ConnectionError as exc:
        msg = "Connection error"
        logger.error(msg)
        raise ConnectionError(msg) from exc
    except requests.exceptions.RequestException:
        logger.error("Other requests exceptions", exc_info=True)


@cache(ttl=config.STATUS_TTL)
async def get_machines_status() -> _MachineStatus:
    site_soup = await _get_site_soup()
    machines_status = {}
    try:
        for washing_machine in site_soup.find_all("div", class_=re.compile(r"col mb-3 childItem child.*")):
            num = int(washing_machine.find("div", class_="text-center").text)
            status = re.search(
                r"[^ ].*[^ ]",
                washing_machine.find_all("div", class_="text-center")[1].text.replace("\n", "")
                ).group()
            machines_status.update({num: status})
        return machines_status
    except AttributeError:
        logger.error("Search machine status: some information has not been found, "
                     "a change in the search algorithm is required")
        return ()


@cache(ttl=config.TIME_LAST_UPDATE_TTL)
async def get_time_last_update() -> _TimeLastUpdate:
    site_soup = await _get_site_soup()
    try:
        time_last_update = site_soup.find("div", attrs={"data-toggle": "tooltip"}).text
        date = re.search(r"\d\d\.\d\d\.\d{4}", time_last_update).group()
        time = re.search(r"\d\d:\d\d", time_last_update).group()
        return tuple([date, time])
    except AttributeError:
        logger.error("Search time last update: some information has not been found, "
                     "a change in the search algorithm is required")
        return tuple()


async def get_machines() -> Sequence[Machines]:
    site_soup = await _get_site_soup()
    result = []
    try:
        for machine in site_soup.find_all("div", class_=re.compile(r"col mb-3 childItem child.*")):
            num = int(machine.find("div", class_="text-center").text)
            kind = machine.div["title"]
            prise = machine.find("span", class_=re.compile(r"pl-1 pr-1 withTooltip.*")).text
            prise = int(re.search(r"\d+", prise).group())
            result.append(Machines(
                id=num,
                type=kind,
                prise=prise
            ))
        return tuple(result)
    except AttributeError:
        logger.error("Search machines: some information has not been found, "
                     "a change in the search algorithm is required")
        return ()
