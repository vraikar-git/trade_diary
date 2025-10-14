from pathlib import Path
import toml


parent_dir = Path(__file__).parent
app_root = parent_dir.parent.parent
try:
    with open(parent_dir / "config.toml", "r") as f:
        config = toml.load(
            f,
        )
        LOGS_DIR = app_root / Path(config["log"]["path"])
        LOG_FILE = LOGS_DIR / config["log"]["file_name"]
        DB_PATH = app_root / Path(config["database"]["path"])
        DB_NAME = config["database"]["db_name"]

except FileNotFoundError:
    raise FileNotFoundError("Configuration file 'config.toml' not found.")
