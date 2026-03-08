import logging
from typing import Final
from dotenv import load_dotenv

from app.configuration import configure

logger = logging.getLogger(__name__)
logger.info("Configuring application...")

load_dotenv(override=True)
configuration = configure()
