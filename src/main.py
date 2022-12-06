import time
import datetime
import threading
import tkinter as tk
# RPi dependency
import spidev
import RPi.GPIO as GPIO

win = tk.Tk()

# Button High/Low
isOffList = []
# Button list
btnList = []
# Label list
lblList =[]

lblClock = None

# GPIO input pin list
inputPinList = []
# GPIO output pin list
outputPinList = [17, 27, 22, 23, 24]

# SPI
spi = None
# SPI - Channel 0
ch0 = 0x00

def init():
    initGPIO()
    initGUI()
    initSPI()
    
    # SPI 통신에서 수신을 위한 thread
    tSpi = threading.Thread(target=waitInput, args=())
    tSpi.daemon=True
    tSpi.start()

    # 시간 표시
    printClock()

def initGUI():
    # print("initGUI called...")
    global lblClock
    lblClock = tk.Label(win, text="##:##:##")
    lblClock.place(x=100, y=0, width=200)

    for i in range(0, 5):
        strIsOffBtn = ""
        if isOffList[i]:
            strIsOffBtn = "Off"
        else:
            strIsOffBtn = "On"

        btn = tk.Button(win, text="GPIO {} {}".format(outputPinList[i], strIsOffBtn), command=lambda no=i: onBtnClick(no))
        btn.place(x=0, y=50*(i+1), width=100)
        btnList.append(btn)

    lblCaptionList = ["Channel", "Read", "OutAdc", "Voltage"]
    for i, v in enumerate(lblCaptionList):
        lbl = tk.Label(win, text=v)
        lbl.place(x=150, y=50*(i+1), width=50)

    for i in range(0, 4):
        lbl = tk.Label(win, text="-")
        lbl.place(x=200, y=50*(i+1), width=100)
        lblList.append(lbl)
	
    win.title("Solenoid Valve Controller")
    win.geometry("400x400+200+200")
    win.protocol("WM_DELETE_WINDOW", onWinClose)

def onWinClose():
    # print("onWinClose called...")
    spi.close()
    setOutput(GPIO.LOW)
    GPIO.cleanup()
    win.destroy()

def onBtnClick(no):
    nPin = outputPinList[no]
    btn = btnList[no]
    isOff = isOffList[no]
    if isOff:
        GPIO.output(nPin, GPIO.LOW)
        print("GPIO {} ==> Low".format(nPin))
        isOffList[no] = False
        btn.config(text="GPIO {} On".format(nPin))
    else:
        GPIO.output(nPin, GPIO.HIGH)
        print("GPIO {} ==> High".format(nPin))
        isOffList[no] = True
        btn.config(text="GPIO {} Off".format(nPin))
    	
    # 0.1 sec wait
    time.sleep(0.1)
    
def initGPIO():
    # print("initGPIO called...")
    # GPIO.BCM or GPIO.BOARD
    GPIO.setmode(GPIO.BCM)
    
    ##########################
    # BCM => BOARD
    ##########################
    # GPIO 5 => 29
    # GPIO 6 => 31
    # GPIO 13 => 33
    # GPIO 19 => 35
    # GPIO 26 => 37
    ##########################
    for nPin in inputPinList:
        GPIO.setup(nPin, GPIO.IN)
    
    for nPin in outputPinList:
        GPIO.setup(nPin, GPIO.OUT)
        print("pin {} ==> set to out".format(nPin))

    for i in range(0, 5):
        isOffList.append(False)
    
def initSPI():
    # print("initSPI called...")
    global spi
    spi=spidev.SpiDev()
    # (bus, device)
    spi.open(0,0)
    spi.max_speed_hz = 1000000
    spi.bits_per_word = 8

def setOutput(level):
    for nPin in outputPinList:
        GPIO.output(nPin, level)

def measure(ch):
    try:
        read = spi.xfer2([1, (8+ch)<<4, 0])
        outAdc = ((read[1]&3) << 8) + read[2]
        v = (outAdc * 3.3) / 1024
        print("[Ch {}] r:[{}], out:[{}],v:{} V".format(0, read, outAdc, v))
        
        printLblList = [str(ch), str(read), str(outAdc), str(v)]
        for i, v in enumerate(printLblList):
            lblList[i].config(text=v)
    except Exception as e:
        print("Ignore Exception cause : ", e)

    return v
    
def waitInput():
    # print("waitInput called...")
    try:
        while True:
            '''
            # GPIO 입력에 의한 출력이 필요할 경우,
            if pin_in_17:
                GPIO.output(18, GPIO.HIGH)
            '''
            
            # SPI 입력
            voltage = measure(ch0)
            # print("ch0={} V, ch1={} V".format(voltage))
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

def printClock():
    lblClock.config(text=getNow())

    # 1초 마다 호출
    tClock = threading.Timer(1, printClock)
    tClock.daemon = True
    tClock.start()

def getNow():
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

if __name__ == "__main__":
    init()
    win.mainloop()
