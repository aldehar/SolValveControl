import datetime

# error log
def e(tag, msg):
    printLog("ERROR", tag, msg)

# warning log
def w(tag, msg):
    printLog("WARN", tag, msg)

# debug log
def d(tag, msg):
    printLog("DEBUG", tag, msg)

# verbose log
def v(tag, msg):
    printLog("VERBOSE", tag, msg)

# info log
def i(tag, msg):
    printLog("INFO", tag, msg)

# 현재 시간
def getNow():
    """현재 시간

    Returns:
        string: ex> '2023-09-20 09:28'
    """
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

# 로그 출력
def printLog(logLevel, tag, msg):
    print("[{}][{}][{}] {}".format(getNow(), logLevel, tag, msg))
