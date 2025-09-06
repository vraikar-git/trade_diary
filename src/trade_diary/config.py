from pathlib import Path
import toml



parent_dir = Path(__file__).parent
try :
    with open(parent_dir / "config.toml", "r") as f:
        config = toml.load(f, )
        LOGS_DIR = parent_dir / Path(config['log']['path'])
        LOG_FILE = LOGS_DIR / config['log']['file_name']
        DB_PATH = parent_dir / Path(config['database']['path'])
        DB_NAME = config['database']['db_name']
        DROPBOX_PATH = config['dropbox_backup']['dropbox_path']
        LAST_BACKUP = config['dropbox_backup'].get('last_backup', None)
        BACKUP_INTERVAL = config['dropbox_backup'].get('backup_interval', 7)

except FileNotFoundError:
    raise FileNotFoundError("Configuration file 'config.toml' not found.")


def update_last_backup(new_date):
    try:
        with open(parent_dir / "config.toml", "r") as f:
            config = toml.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("Configuration file 'config.toml' not found.")
    
    if 'dropbox_backup' not in config:
        config['dropbox_backup'] = {}

    config['dropbox_backup']['last_backup'] = new_date
    try:
        with open(parent_dir / "config.toml", "w") as f:
            toml.dump(config, f)
    except Exception as e:
        raise RuntimeError(f"Failed to update configuration file: {e}")
