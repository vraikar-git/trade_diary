from datetime import date
import logging
import src.trade_diary.config as config
from src.trade_diary.backup import backup_database


from .db_interface import init_db

try:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    raise RuntimeError(f"Unable to create logs directory {config.LOGS_DIR}: {e}")

try:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception as e:
    raise RuntimeError(f"Unable to create database directory {config.DB_PATH.parent}: {e}")


logging_format = "%(asctime)s %(levelname)s [%(module)s:%(filename)s:%(lineno)d] %(message)s"
formatter = logging.Formatter(logging_format)
logging.basicConfig(
    filename=config.LOG_FILE,
    filemode='a',
    level=logging.DEBUG,
    format=logging_format
)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logging.getLogger().addHandler(console)
logging.debug("Starting Trade Diary Application")

today = date.today()
dropbox_path = config.DROPBOX_PATH
db = str(config.DB_PATH) + '/' + config.DB_NAME
db_url = f"sqlite:///{db}"

if config.LAST_BACKUP is None or (today - config.LAST_BACKUP).days > config.BACKUP_INTERVAL:
    current_backup_date = backup_database(db, dropbox_path)
    if current_backup_date:
        config.LAST_BACKUP = current_backup_date
        config.update_last_backup(current_backup_date)
        logging.info(f"Backup completed on {config.LAST_BACKUP}")
    else:
        logging.error("Backup failed. LAST_BACKUP remains unset.")
else:
    logging.info(f"No backup needed. Last backup was on {config.LAST_BACKUP}")


init_db(db_url)