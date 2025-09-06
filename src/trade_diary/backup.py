import logging
import dotenv
from datetime import date
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

def backup_database(db_path, dropbox_path):
    logging.info("Starting database backup to Dropbox...")
    DROPBOX_REFRESH_TOKEN = dotenv.get_key(dotenv.find_dotenv(), "DROPBOX_REFRESH_TOKEN")
    DROPBOX_APP_KEY = dotenv.get_key(dotenv.find_dotenv(), "DROPBOX_APP_KEY")
    DROPBOX_APP_SECRET = dotenv.get_key(dotenv.find_dotenv(), "DROPBOX_APP_SECRET")

    if DROPBOX_REFRESH_TOKEN and DROPBOX_APP_KEY and DROPBOX_APP_SECRET:
        logging.info("Dropbox API credentials are set.")
        with dropbox.Dropbox(
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET
        ) as dbx:
            try:
                dbx.users_get_current_account()
                logging.info("Dropbox account linked successfully.")
            except AuthError as err:
                logging.error("ERROR: Invalid access token; Backup Failed")

            try:
                with open(db_path, 'rb') as f:
                    today_date = date.today()
                    today_str = today_date.strftime("%Y%m%d")
                    backup_file_name = f"trade_diary_backup_{today_str}.db"
                    full_dropbox_path = f"{dropbox_path}/{backup_file_name}"
                    dbx.files_upload(f.read(), full_dropbox_path, mode=WriteMode('overwrite'))
                logging.info(f"Database backup successful: {full_dropbox_path}")
                return today_date

            except FileNotFoundError:
                logging.error(f"ERROR: Database file not found at {db_path}; Backup Failed")
                return None

            except ApiError as err:
                logging.error(f"API error during backup: {err}; Backup Failed")
                return None

            except Exception as e:
                logging.error(f"Unexpected error during backup: {e}; Backup Failed")
                return None
    else:
        logging.error("ERROR: Dropbox API credentials are not set; Backup Failed")
        return None




if __name__ == "__main__":
    db_path = "/home/vijay/vijay/projects/trade_diary/src/trade_diary/db/trading_journal.db"
    dropbox_path = "/Trading Data/trading_db_backups"
    backup_database(db_path, dropbox_path)