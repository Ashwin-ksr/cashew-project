import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
DATA_FOLDER_PATH = Path(__file__).resolve().parents[2] / "data"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"