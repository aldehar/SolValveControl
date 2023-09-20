# temp file, prevent compile error

TAG = "GPIO"

HIGH = 1
LOW = 0

BCM = 0
BOARD = 1

IN = 0
OUT = 1

def setup(nPin, nInOut, initial):
    print("[{}] SetUp - Pin : {}, InOut : {}, Initial : {}".format(TAG, nPin, nInOut, initial))

def setmode(nMode):
    print("[{}] Mode - {}".format(TAG, nMode))

def input(nPin, nLevel):
    print("[{}] Input - {}, Level : {}".format(TAG, nPin, nLevel))

def output(nPin, nLevel):
    print("[{} Pin - {}, Level : {}] ".format(TAG, nPin, nLevel))
    pass

def cleanup():
    print("[{}] Cleanup...".format(TAG))
    pass