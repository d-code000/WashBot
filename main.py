import asyncio
import yaml
import logging.config

import webparser


async def main():
    logging_config = yaml.safe_load(open("logging.yaml", 'rt').read())
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(__name__)


if __name__ == "__main__":
    asyncio.run(main())
