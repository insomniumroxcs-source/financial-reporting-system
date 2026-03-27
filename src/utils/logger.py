"""
Centralized logging configuration.
Console output at INFO level, file output at DEBUG level.
"""
import logging
import os
import yaml


def setup_logger(name: str = "financial_pipeline") -> logging.Logger:
    """Configure and return the application logger."""
    # Load config
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config.yaml"
    )
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        log_cfg = config.get("logging", {})
    except FileNotFoundError:
        log_cfg = {}

    console_level = getattr(logging, log_cfg.get("console_level", "INFO"))
    file_level = getattr(logging, log_cfg.get("file_level", "DEBUG"))
    log_file = log_cfg.get("log_file", "logs/pipeline.log")

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(funcName)s │ %(message)s"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger
