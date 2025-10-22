from datetime import date
import logging
import src.trade_diary.config as config


from .db_interface import init_db

try:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    raise RuntimeError(f"Unable to create logs directory {config.LOGS_DIR}: {e}")

try:
    config.DB_PATH.mkdir(parents=True, exist_ok=True)
except Exception as e:
    raise RuntimeError(
        f"Unable to create database directory {config.DB_PATH.parent}: {e}"
    )


logging_format = (
    "%(asctime)s %(levelname)s [%(module)s:%(filename)s:%(lineno)d] %(message)s"
)
formatter = logging.Formatter(logging_format)
logging.basicConfig(
    filename=config.LOG_FILE, filemode="a", level=logging.DEBUG, format=logging_format
)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logging.getLogger().addHandler(console)
logging.debug("Starting Trade Diary Application")


db = str(config.DB_PATH) + "/" + config.DB_NAME
db_url = f"sqlite:///{db}"

init_db(db_url)
