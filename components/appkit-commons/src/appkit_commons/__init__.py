from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# init first to prevent circular dependencies
BASE_PATH: Final[Path] = Path.cwd()
CONFIGURATION_PATH: Final[Path] = BASE_PATH / "configuration"

# initialize logging and .env before everything else
load_dotenv(override=True)
