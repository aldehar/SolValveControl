import threading
import RPi.GPIO as GPIO
import spidev
import time

import log as Log

class Comm:
    TAG = "RPiManager.Comm"

    # 릴레이의 출력단자에 +, - 전압을 결선했는지 여부에 따라...
    IS_PNP = True

    # SPI 쓰레드 활성화 변수
    isRunning = False

    # GPIO input pin list
    inputPinList = []
    # GPIO output pin list[BCM]
    outputPinList = [17, 27, 22, 23, 24, 25]

    spi = None
    ch0 = 0x00
    ch1 = 0x10
    # SPI 통신대기 시간(단위:초)
    waitTime = 0.5

    # 생성자
    def __init__(self, win):
        super().__init__()
        
        self.win = win
        
        self.initGPIO()
        self.initSPI()
    
    # 소멸자
    def __del__(self):
        self.release()

    # 자원 해제
    def release(self):
        self.isRunning = False
        GPIO.cleanup()
        self.spi.close()

    # GPIO 초기화
    def initGPIO(self):
        # GPIO.BCM or GPIO.BOARD
        GPIO.setmode(GPIO.BCM)
        
        ##########################
        # BCM => BOARD
        ##########################
        # GPIO 17 => 11 - Valve 1
        # GPIO 27 => 13 - Valve 2
        # GPIO 22 => 15 - Valve 3
        # GPIO 23 => 16 - Vavle 4
        # GPIO 24 => 18 - Valve 5
        # GPIO 25 => 18 - Motor
        ##########################
        for nPin in self.inputPinList:
            GPIO.setup(nPin, GPIO.IN)
        
        initLevel = GPIO.LOW
        if self.IS_PNP:
            initLevel = GPIO.LOW
        else:
            initLevel = GPIO.HIGH

        for nPin in self.outputPinList:
            GPIO.setup(nPin, GPIO.OUT, initial=initLevel)
            Log.d(self.TAG, "pin {} ==> set to OUT, initial = GPIO.HIGH".format(nPin))

    # SPI 통신 초기화
    def initSPI(self):
        self.spi = spidev.SpiDev()
        # (bus, device)
        self.spi.open(0,0)
        self.spi.max_speed_hz = 1000000
        self.spi.bits_per_word = 8
        
        # SPI 통신에서 수신을 위한 thread
        self.isRunning = True
        tSpi = threading.Thread(target=self.waitInput, args=())
        tSpi.daemon = True
        tSpi.start()

    # 모든 출력 핀 세팅
    def setAllOutput(self, level):
        for nPin in self.outputPinList:
            GPIO.output(nPin, level)

    # 특정 출력 핀 세팅
    def setPinOutput(self, nPin, level):
        Log.d(self.TAG, "setPinOutput() Pin:{}, level {}".format(nPin, level))
        GPIO.output(nPin, level)

    # 번호에 따른 출력
    def setOutput(self, no, isHigh):
        try:
            output = GPIO.LOW
            if isHigh:
                if self.IS_PNP:
                    output = GPIO.HIGH
                else:
                    output = GPIO.LOW
            else:
                if self.IS_PNP:
                    output = GPIO.LOW
                else:
                    output = GPIO.HIGH

            if no <= len(self.outputPinList):
                self.setPinOutput(self.outputPinList[no-1], output)

        except Exception as e:
            Log.e(self.TAG, "setOutput() Exception cause : {}".format(e))

    # SPI 통신 read
    def readSPI(self, ch):
        try:
            read = self.spi.xfer2([1, (8+ch)<<4, 0])
            outAdc = ((read[1]&3) << 8) + read[2]
            v = round(((outAdc * 3.3) / 1024), 4)
            pressure = round((v-0.9)/0.4, 3)
            dictRtn = {"ch": ch, "read":read, "outAdc": outAdc, "v":v, "pressure":pressure}

            self.win.onRecvResult(dictRtn)
        except Exception as e:
            Log.w(self.TAG, "readSPI() Exception cause : {}".format(e))

        return v
        
    # SPI 통신 대기
    def waitInput(self):
        try:
            while self.isRunning:
                # SPI 입력
                self.readSPI(self.ch0)
                # self.readSPI(self.ch1)
                time.sleep(self.waitTime)
        except KeyboardInterrupt:
            pass
