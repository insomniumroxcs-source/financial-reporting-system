"""
Utility helpers: config loader, retry decorator, date utilities.
"""
import os
import time
import functools
import yaml
from typing import Any, Dict


def load_config() -> Dict[str, Any]:
    """Load the YAML configuration file."""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config.yaml"
    )
    config_path = os.path.abspath(config_path)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_field_mapping(config: Dict[str, Any] = None) -> Dict[str, list]:
    """
    Return the XBRL → human-readable field mapping from config.
    Keys are standardised names, values are lists of possible source names.
    """
    if config is None:
        config = load_config()
    return config.get("field_mapping", {})


def retry(max_retries: int = 3, backoff_factor: float = 1.0, exceptions=(Exception,)):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for wait time between retries.
        exceptions: Tuple of exception types to catch and retry.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait = backoff_factor * (2 ** attempt)
                        time.sleep(wait)
            raise last_exception
        return wrapper
    return decorator


def ensure_directories(config: Dict[str, Any] = None):
    """Create all necessary output directories from config."""
    if config is None:
        config = load_config()
    output = config.get("output", {})
    for key, path in output.items():
        os.makedirs(path, exist_ok=True)
    # Also ensure logs directory
    log_file = config.get("logging", {}).get("log_file", "logs/pipeline.log")
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
