import os
import logging.config
import yaml
from pathlib import Path
from urllib.parse import quote

def get_standby_url():
    if os.getenv('STANDBY_URL'):
        return os.getenv('STANDBY_URL')

    host = os.getenv('STANDBY_HOST')
    port = os.getenv('STANDBY_PORT', '5432')
    database = os.getenv('STANDBY_NAME')
    username = os.getenv('STANDBY_USERNAME')
    password = os.getenv('STANDBY_PASSWORD', '')

    if not host or not database or not username:
        raise ValueError("STANDBY_HOST, STANDBY_NAME ve STANDBY_USERNAME gerekli")

    password_part = f":{quote(password)}" if password else ""
    return f"postgresql://{quote(username)}{password_part}@{host}:{port}/{database}"


def get_primary_url():
    if os.getenv('PRIMARY_URL'):
        return os.getenv('PRIMARY_URL')

    host = os.getenv('PRIMARY_HOST')
    port = os.getenv('PRIMARY_PORT', '5432')
    database = os.getenv('PRIMARY_NAME')
    username = os.getenv('PRIMARY_USERNAME')
    password = os.getenv('PRIMARY_PASSWORD', '')

    if not host or not database or not username:
        raise ValueError("PRIMARY_HOST, PRIMARY_NAME ve PRIMARY_USERNAME gerekli!")

    password_part = f":{quote(password)}" if password else ""
    return f"postgresql://{quote(username)}{password_part}@{host}:{port}/{database}"


def get_rabbitmq_url():
    if os.getenv('RABBITMQ_URL'):
        return os.getenv('RABBITMQ_URL')

    host = os.getenv('RABBITMQ_HOST')
    port = os.getenv('RABBITMQ_PORT', '5672')
    username = os.getenv('RABBITMQ_USERNAME', 'guest')
    password = os.getenv('RABBITMQ_PASSWORD', 'guest')
    vhost = os.getenv('RABBITMQ_VHOST', '/')

    if not host:
        raise ValueError("RABBITMQ_HOST gerekli!")

    password_part = f":{quote(password)}" if password else ""
    vhost_part = f"/{quote(vhost)}" if vhost != '/' else vhost
    return f"amqp://{quote(username)}{password_part}@{host}:{port}{vhost_part}"


def get_sqlite_url():
    return "sqlite:///:memory:"


def setup_logger():
    """
    Loads and applies the logging configuration from a YAML file.

    It attempts to find `logger_config.yaml` in the `config/base/` directory
    relative to the project root. It also ensures the 'logs' directory exists.
    If the configuration file is not found or an error occurs during loading,
    it falls back to a basic logging configuration.
    """
    project_root = Path(__file__).resolve().parent.parent
    log_config_yaml_path = project_root / "config/base/logger_config.yml"
    logs_dir = project_root / "logs"

    # Ensure the logs directory exists
    if not logs_dir.exists():
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            print(f"Log directory created: {logs_dir}", flush=True)
        except OSError as e:
            print(f"ERROR: Could not create log directory: {logs_dir}. Error: {e}", flush=True)

    # Check if the YAML configuration file exists
    if not log_config_yaml_path.exists():
        print(f"ERROR: Logging configuration file not found: {log_config_yaml_path}", flush=True)
        # Fallback to basic logging if the config file is missing
        logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
        return

    try:
        with open(log_config_yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        logging.config.dictConfig(config)

        initial_logger = logging.getLogger(__name__)
        initial_logger.info(f"Logging successfully configured from YAML. Log files are in: {logs_dir}")

    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse YAML logging configuration file: {e}", flush=True)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading logging configuration: {e}", flush=True)
