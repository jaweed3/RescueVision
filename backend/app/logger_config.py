import logging
import sys

def setup_logging():
    """Configures the root logger for the entire application."""
    # Prevent duplicate handlers if setup is called multiple times
    if logging.getLogger().hasHandlers():
        return

    # 1. Define a shared format string
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 2. Create a Console Handler (Outputs to terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    # 3. Create a File Handler (Outputs to app.log)
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)

    # 4. Configure the Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything at the root level
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
