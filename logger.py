import logging
import logging.handlers
import os
import colorama
import datetime
if os.name != "nt": # Only need to import this for Linux
    try:
        from cysystemd import journal
    except:
        pass

tz = datetime.datetime.now().astimezone().tzinfo
now = datetime.datetime.now(tz)
formatted_time = now.strftime("%d-%m-%Y %H:%M:%S")

def setupLogging(base_path: str) -> None:
    """Setup logging for the Discord Bot.

    Args:
        base_path (str): The base path of the bot, should target "src".
    """
    log_path = os.path.join(base_path, "Logs")

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    # Setup colorama for Windows machines.
    if os.name == "nt":
        colorama.init(autoreset=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.handlers.TimedRotatingFileHandler(
        filename = os.path.join(log_path, "bot_log.log"),
        when = "D",
        atTime = datetime.time(hour=0, minute=5, tzinfo=tz), # Log roll over will occur a little after the midnight when the bot restarts.
        backupCount = 21, # 21 days/3 weeks worth of logs will be kept, each day the oldest one will be deleted.
        encoding = "utf-8",
    )
    handler.setFormatter(logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%d-%m-%Y %H:%M:%S", style="{"))
    logger.addHandler(handler)
    if os.name != "nt": # Add log handler for Linux's systemd journal system.
        try:
            logger.addHandler(journal.JournaldLogHandler())
        except:
            pass
    
    logging.info("\n") # To separate new logs in the same day

# A log function to both log to the log file and print to the console, printing to the console can be optional.
def log(msg: str = "", log_level: int = 0, console: bool = True) -> None:
    """Logs a message to both the console and the log file.
    Printing to console can be optional. Defaults to INFO logging with console set to True.

    Args:
        msg (str, optional): Message to be logged and printed to console. Message will be colored depending on level. Defaults to "".
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
        if console: print(colorama.Fore.YELLOW + f'[{formatted_time}] WARN: {msg}' + colorama.Fore.WHITE)
        logging.warning(msg)
        return
    elif log_level == 2:
        if console: print(colorama.Fore.RED + f'[{formatted_time}] ERROR: {msg}' + colorama.Fore.WHITE)
        logging.error(msg)
        return
    elif log_level == 3:
        if console: print(colorama.Fore.WHITE + colorama.Back.RED + f'[{formatted_time}] CRITICAL: {msg}' + colorama.Fore.WHITE)
        logging.critical(msg)
        return

    if console:
        print(f'[{formatted_time}] INFO: {msg}')
    logging.info(msg)
