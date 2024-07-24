import logging
from logging import handlers
import os
import colorama
import datetime
from cysystemd import journal

formatted_time = datetime.datetime.now(datetime.datetime.now().astimezone().tzinfo).strftime("%d-%m-%Y %H:%M:%S")

def setup_logging(base_path: str) -> None:
    """Setup logging for the Discord Bot

    Args:
        base_path (str): The base path of the bot, should target "src"
    """
    log_path = os.path.join(base_path, "Logs")

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    # Setup colorama for Windows machines
    if os.name == "nt":
        colorama.init(autoreset=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(
        filename = os.path.join(log_path, f"bot_log-({datetime.datetime.now().strftime('%d-%m-%Y %H-%M-%S')}).log"), # Log location
        mode= "w", # Mode to write to the log
        encoding = "utf-8", # Log encoding
    )
    handler.setFormatter(logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%d-%m-%Y %H:%M:%S", style="{"))
    logger.addHandler(handler)
    logger.addHandler(journal.JournaldLogHandler())

# A log function to both log to the log file and print to the console, printing to the console can be optional
def log(msg: str, log_level: int = 0, console: bool = True) -> None:
    """Logs a message to both the console and the log file.
    Printing to console can be optional. Defaults to INFO logging with console set to True.

    Args:
        msg (str): Message to be logged and printed to console. Message will be colored depending on level.
        log_level (int, optional):
            Level to log the message:
                0 = INFO (White)
                1 = WARN (Yellow)
                2 = ERROR (Red Text)
                3 = CRITICAL (White Text, Red Background)
            Defaults to 0.
        console (bool, optional): Print the log message to console. Message will still be logged to the log file.
    """

    if log_level == 1:
        if console: print(colorama.Fore.YELLOW + f'[{formatted_time}] WARN: {msg}')
        logging.warn(msg)
        return
    elif log_level == 2:
        if console: print(colorama.Fore.RED + f'[{formatted_time}] ERROR: {msg}')
        logging.error(msg)
        return
    elif log_level == 3:
        if console: print(colorama.Fore.WHITE + colorama.Back.RED + f'[{formatted_time}] CRITICAL: {msg}')
        logging.critical(msg)
        return

    if console:
        print(colorama.Fore.WHITE + f'[{formatted_time}] INFO: {msg}')
    logging.info(msg)
