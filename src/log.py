import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# log 출력 형식
formatter = logging.Formatter('[%(asctime)s][%(name)s][%(levelname)s] - %(message)s')

# log를 console에 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# log를 파일에 출력
file_handler = logging.FileHandler('valve.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

#critical log
def c(tag, msg):
    logger.critical("[{}] {}".format(tag, msg))

# error log
def e(tag, msg):
    logger.error("[{}] {}".format(tag, msg))

# warning log
def w(tag, msg):
    logger.warning("[{}] {}".format(tag, msg))

# debug log
def d(tag, msg):
    logger.debug("[{}] {}".format(tag, msg))

# info log
def i(tag, msg):
    logger.info("[{}] {}".format(tag, msg))

# 현재 시간
def getNow():
    """현재 시간

    Returns:
        string: ex> '2023-09-20 09:28'
    """
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime
