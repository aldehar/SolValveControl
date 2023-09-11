import threading
import RPi.GPIO as GPIO
import spidev
import time

comm = None

class Comm:
    # GPIO input pin list
    inputPinList = []
    # GPIO output pin list[BCM]
    outputPinList = [17, 27, 22, 23, 24]

    spi = None
    ch0 = 0x00
    # SPI 통신대기 시간(단위:초)
    waitTime = 0.5

    def __init__(self, win):
        super().__init__()
        
        self.win = win
        
        self.initGPIO()
        self.initSPI()

    def initGPIO(self):
        # GPIO.BCM or GPIO.BOARD
        GPIO.setmode(GPIO.BCM)
        
        ##########################
        # BCM => BOARD
        ##########################
        # GPIO 17 => 11
        # GPIO 27 => 13
        # GPIO 22 => 15
        # GPIO 23 => 16
        # GPIO 24 => 18
        ##########################
        for nPin in self.inputPinList:
            GPIO.setup(nPin, GPIO.IN)
        
        for nPin in self.outputPinList:
            GPIO.setup(nPin, GPIO.OUT)
            print("pin {} ==> set to out".format(nPin))

    # SPI 통신 초기화
    def initSPI(self):
        self.spi=spidev.SpiDev()
        # (bus, device)
        self.spi.open(0,0)
        self.spi.max_speed_hz = 1000000
        self.spi.bits_per_word = 8

        # SPI 통신에서 수신을 위한 thread
        tSpi = threading.Thread(target=self.waitInput, args=())
        tSpi.daemon=True
        tSpi.start()

    # 모든 출력 핀 세팅
    def setAllOutput(self, level):
        for nPin in self.outputPinList:
            GPIO.output(nPin, level)

    # 특정 출력 핀 세팅
    def setPinOutput(self, nPin, level):
        GPIO.output(nPin, level)

    # SPI 통신 read
    def readSPI(self, ch):
        try:
            read = self.spi.xfer2([1, (8+ch)<<4, 0])
            outAdc = ((read[1]&3) << 8) + read[2]
            v = round(((outAdc * 3.3) / 1023), 5)

            # for checking
            # print("[Ch {}] r:[{}], out:[{}],v:{} V".format(0, read, outAdc, v))
            printLblList = [str(ch), str(read), str(outAdc), str(v)]
            '''
            for i, v in enumerate(printLblList):
                print(i, v)
            '''
            self.win.onRecvResult(printLblList)
        except Exception as e:
            print("Ignore Exception cause : ", e)

        return v
        
    # SPI 통신 대기
    def waitInput(self):
        try:
            while True:
                # SPI 입력
                voltage = self.readSPI(self.ch0)
                time.sleep(self.waitTime)
        except KeyboardInterrupt:
            pass

def init(win):
    global comm
    comm = Comm(win)

def setOutput(no):
    if no == 1:
        pass
        #comm.setPinOutput()
    elif no == 2:
        pass
    elif no == 3:
        pass
    elif no == 4:
        pass
    elif no == 5:
        pass
    