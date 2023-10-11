import time
import datetime
import threading
import tkinter as tk
# RPi dependency
import spidev
import RPi.GPIO as GPIO

win = tk.Tk()

IS_PNP = True

# Button High/Low
isOffList = []
# Button list
btnList = []
# Label list
lblList =[]
# Spinbox list
sbList = []
# sv list
svList = []
# set button list
btnSetList = []

lblClock = None

# GPIO input pin list
inputPinList = []
# GPIO output pin list
outputPinList = [17, 27, 22, 23, 24, 25, 12]

# SPI
spi = None
# SPI - Channel 0
ch0 = 0x00

isMotorOn = False

def init():
    initGPIO()
    initGUI()
    initSPI()

    # 시간 표시 - 1초 틱마다 호출
    printClock()

def initGUI():
    global lblClock
    lblClock = tk.Label(win, text="##:##:##", font=("Arial Bold", 12))
    lblClock.place(x=125, y=15, width=200)

    for i, pin in enumerate(outputPinList):
        strIsOffBtn = ""
        if isOffList[i]:
            strIsOffBtn = "Off"
        else:
            strIsOffBtn = "On"
        
        name = "Valve"
        if i == 5:
            name = "Motor"
        elif i > 5:
            name = "Etc"

        lbl = tk.Label(win, text=name +" "+str(i+1), font=("Arial Bold", 9))
        lbl.place(x=50, y=50*(i+1), width=50)

        btn = tk.Button(win, text="GPIO {} {}".format(outputPinList[i], strIsOffBtn), bg="blue", fg="white", command=lambda no=i: onBtnClick(no))
        btn.place(x=100, y=50*(i+1), width=75)
        btnList.append(btn)

    lblCaptionList = ["Channel", "Read", "OutAdc", "Voltage", "Pressure"]
    for i, v in enumerate(lblCaptionList):
        lbl = tk.Label(win, text=v, font=("Arial Bold", 9))
        lbl.place(x=200, y=50*(i+1), width=60)

    maxLength = len(outputPinList)

    for i in range(0, maxLength):
        lbl = tk.Label(win, text="-")
        lbl.place(x=250, y=50*(i+1), width=100)
        lblList.append(lbl)
	
    lineY = 50 * (maxLength) + 50

    lblTimer = tk.Label(win, text="Timer", font=("Arial Bold", 11))
    lblTimer.place(x=50, y=lineY)
    
    lineY = lineY + 25

    for i in range(0, 5):
        lbl = tk.Label(win, text="Valve "+ str(i+1), font=("Arial Bold", 9))
        lbl.place(x=50+75*i, y=lineY, width=50, height=25)

    lineY = lineY + 25
    
    for i in range(0, 5):
        btn = tk.Button(win, text="Disable", bg="orange", fg="white", command=lambda no=i: onToggleBtnClick(no))
        btn.place(x=50+75*i, y=lineY, width=50, height=25)
        btnSetList.append(btn)

    lineY = lineY + 25

    for i in range(0, 5):
        sv = tk.StringVar()
        sv.set("0")
        sb = tk.Spinbox(win, textvariable=sv)
        sb.place(x=50+75*i, y=lineY, width=50)
        sbList.append(sb)
        svList.append(sv)

    win.title("Solenoid Valve Controller")
    win.geometry("450x450+200+200")
    win.protocol("WM_DELETE_WINDOW", onWinClose)

# 윈도우 x키 눌러서 종료시, 호출
def onWinClose():
    spi.close()
    setOutput(GPIO.LOW)
    GPIO.cleanup()
    win.destroy()

def onBtnClick(no):
    global isMotorOn
    nPin = outputPinList[no]
    btn = btnList[no]
    isOff = isOffList[no]
    print("clicked pin : ", nPin)
    # PwM
    if nPin == 12:
        print("isMotorOn :", isMotorOn)
        if isMotorOn:
            level = GPIO.LOW
            if IS_PNP:
                level = GPIO.LOW
            else:
                level = GPIO.HIGH
            isMotorOn = False
            GPIO.output(nPin, level)
            btn.config(text="GPIO {} Off".format(nPin))
            btn.config(bg="blue")
        else:
            level = GPIO.LOW
            if IS_PNP:
                level = GPIO.HIGH
            else:
                level = GPIO.LOW
            isMotorOn = True
            GPIO.output(nPin, level)
            btn.config(text="GPIO {} On".format(nPin))
            btn.config(bg="red")
    else:
        if isOff:
            level = GPIO.HIGH
            if IS_PNP:
                level = GPIO.HIGH
            else:
                level = GPIO.LOW

            GPIO.output(nPin, level)
            print("GPIO {} ==> Low".format(nPin))
            isOffList[no] = False
            btn.config(text="GPIO {} On".format(nPin))
            btn.config(bg="red")
        else:
            level = GPIO.LOW
            if IS_PNP:
                level = GPIO.LOW
            else:
                level = GPIO.HIGH

            GPIO.output(nPin, level)
            print("GPIO {} ==> High".format(nPin))
            isOffList[no] = True
            btn.config(text="GPIO {} Off".format(nPin))
            btn.config(bg="blue")
    	
    # 0.1 sec wait
    time.sleep(0.1)
    
def onToggleBtnClick(no):
    btn = btnSetList[no]
    if btn["text"] == "Enable":
        btn.config(text="Disable")
        btn.config(bg="orange")
    elif btn["text"] == "Disable":
        btn.config(text="Enable")
        btn.config(bg="green")
    else:
        print("[WARN] unknown text : ", btn["text"])

def initGPIO():
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
    for nPin in inputPinList:
        GPIO.setup(nPin, GPIO.IN)
    
    initLevel = GPIO.LOW
    if IS_PNP:
        initLevel = GPIO.LOW
    else:
        initLevel = GPIO.HIGH
        
    for nPin in outputPinList:
        GPIO.setup(nPin, GPIO.OUT, initial=initLevel)
        print("pin {} ==> set to out".format(nPin))

    for i, pin in enumerate(outputPinList):
        isOffList.append(True)
    
def initSPI():
    global spi
    spi=spidev.SpiDev()
    # (bus, device)
    spi.open(0,0)
    spi.max_speed_hz = 1000000
    spi.bits_per_word = 8

    # SPI 통신에서 수신을 위한 thread
    tSpi = threading.Thread(target=waitInput, args=())
    tSpi.daemon=True
    tSpi.start()

def setOutput(level):
    for nPin in outputPinList:
        GPIO.output(nPin, level)

def readSPI(ch):
    try:
        read = spi.xfer2([1, (8+ch)<<4, 0])
        outAdc = ((read[1]&3) << 8) + read[2]
        v = round(((outAdc * 3.3) / 1024), 4)
        pressure = round((v-0.9)/0.4, 3)

        # for checking
        #print("[Ch {}] r:[{}], out:[{}],v:{} V, pressure:{} bar".format(0, read, outAdc, v, pressure))
        printLblList = [str(ch), str(read), str(outAdc), str(v), str(pressure)+ " bar"]
        for i, v in enumerate(printLblList):
            lblList[i].config(text=v)
    except Exception as e:
        print("Ignore Exception cause : ", e)

    return v
    
def waitInput():
    try:
        while True:
            # SPI 입력
            voltage = readSPI(ch0)

            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

# 1초 마다 호출 됨
def printClock():
    lblClock.config(text=getNow())

    for i, sv in enumerate(svList):
        btn = btnSetList[i]
        btnText = btn["text"]
        if btnText == "Enable":
            s = sv.get()
            sec = int(s)
            if sec > 0:
                sec -= 1
                sv.set(sec)

                if sec == 0:
                    btn.config(text="Disable")

    tClock = threading.Timer(1, printClock)
    tClock.daemon = True
    tClock.start()

# 현재시간
def getNow():
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

if __name__ == "__main__":
    init()
    win.mainloop()
