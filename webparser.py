import re
import logging.config
from typing import Union

import requests
from bs4 import BeautifulSoup
from cashews import Cache

import config


_MachineStatus = tuple[tuple[Union[int, str], ...], ...]
_TimeLastUpdate = tuple[str, ...]

logger = logging.getLogger(__name__)
cache = Cache()
cache.setup("mem://")


async def _get_site_soup() -> BeautifulSoup:
    logger.info(f"Connecting to site {config.SITE_URL}")
    try:
        r = requests.get(config.SITE_URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        return soup
    except requests.exceptions.HTTPError:
        logger.error(f"HTTP error, status code {r.status_code}")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error")
    except requests.exceptions.RequestException:
        logger.error("Other requests exceptions", exc_info=True)


@cache(ttl="10s")
async def get_machines_status() -> _MachineStatus:
    site_soup = await _get_site_soup()
    machines_status = []
    for washing_machine in site_soup.find_all("div", class_=re.compile(r"col mb-3 childItem child.*")):
        num = int(washing_machine.find("div", class_="text-center").text)
        status = re.search(
            r"[^ ].*[^ ]",
            washing_machine.find_all("div", class_="text-center")[1].text.replace("\n", "")
            ).group()
        kind = washing_machine.div["title"]
        machines_status.append(tuple([num, status, kind]))
    return tuple(machines_status)


@cache(ttl="1m")
async def get_time_last_update() -> _TimeLastUpdate:
    site_soup = await _get_site_soup()
    time_last_update = site_soup.find("div", attrs={"data-toggle": "tooltip"}).text
    date = re.search(r"\d\d\.\d\d\.\d{4}", time_last_update).group()
    time = re.search(r"\d\d:\d\d", time_last_update).group()
    return tuple([date, time])
