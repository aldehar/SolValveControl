import sys
import datetime
import threading
from functools import partial
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel,QSpinBox, QComboBox
from PyQt5.QtGui import *

import RPiUtil

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.printClock()

        # 라즈베리파이 관련 인스턴스
        self.rpiUtil = RPiUtil.init(self)

    def initUI(self):
        oImg = {
            "on":"res/imgs/on.png",
            "off":"res/imgs/off,png",
            "bg":"res/imgs/printing1.png",
            "valve":"res/imgs/printing2.png",
        }
    
        # 배경
        self.lblBg = QLabel("", self)
        self.lblBg.move(0, 15)
        self.lblBg.resize(600, 400)
        self.pixmap = QPixmap()
        self.pixmap.load(oImg["bg"])
        self.pixmapVar = self.pixmap.scaledToWidth(600)
        self.lblBg.setPixmap(self.pixmapVar)
        self.lblBg.setStyleSheet("background-color:#e0e0e0;")
        
        # 타이머
        self.lblTime = QLabel("", self)
        self.lblTime.move(250, 0)
        self.lblTime.resize(150, 25)
        
        # 압력 게이지
        self.pressure = QLabel("-", self)
        self.pressure.move(235, 215)
        self.pressure.resize(250, 50)
        
        #선
        self.lineList = [
            {"no":1, "o":None, "title":"1", "x":255, "y":125, "w":90,"h":5},
            {"no":2, "o":None, "title":"2", "x":345, "y":125, "w":120,"h":5},
            {"no":3, "o":None, "title":"3", "x":495, "y":125, "w":45,"h":5},
            {"no":4, "o":None, "title":"4", "x":375, "y":130, "w":5,"h":90},
            {"no":5, "o":None, "title":"5", "x":180, "y":215, "w":110,"h":5},
            {"no":6, "o":None, "title":"6", "x":340, "y":215, "w":120,"h":5},
            {"no":7, "o":None, "title":"7", "x":495, "y":215, "w":45,"h":5},
            {"no":8, "o":None, "title":"8", "x":277, "y":220, "w":5,"h":68},
            {"no":9, "o":None, "title":"9", "x":277, "y":283, "w":75,"h":5},
            {"no":10, "o":None, "title":"10", "x":400, "y":285, "w":145,"h":5}
        ]
        
        for lblLine in self.lineList:
            lblLine["o"] = QLabel("", self)
            lblLine["o"].setText(lblLine["title"])
            lblLine["o"].move(lblLine["x"], lblLine["y"])
            lblLine["o"].resize(lblLine["w"], lblLine["h"])
            lblLine["o"].setStyleSheet("background-color:red;")
        
        # 라벨
        self.labelList = [
            {"no":1, "o":None, "title":"#1 Sol", "x":290, "y":60, "w":55,"h":25},
            {"no":2, "o":None, "title":"#2 Sol", "x":440, "y":55, "w":55,"h":25},
            {"no":3, "o":None, "title":"#3 Sol", "x":440, "y":145, "w":55,"h":25},
            {"no":4, "o":None, "title":"#4 Sol", "x":290, "y":147, "w":55,"h":25},
            {"no":5, "o":None, "title":"#5 Sol", "x":350, "y":235, "w":55,"h":25},
        ]
        
        for lbl in self.labelList:
            lbl["o"] = QLabel(lbl["title"], self)
            lbl["o"].move(lbl["x"], lbl["y"])
            lbl["o"].resize(lbl["w"], lbl["h"])

        # 밸브 버튼(NOP)
        self.btnList = [
            {"no":1, "o":None, "title":"1", "isOpen":False, "x":290, "y":80, "w":55,"h":60, "img":oImg["valve"]},
            {"no":2, "o":None, "title":"2", "isOpen":False, "x":440, "y":75, "w":55,"h":60, "img":oImg["valve"]},
            {"no":3, "o":None, "title":"3", "isOpen":False, "x":440, "y":165, "w":55,"h":60, "img":oImg["valve"]},
            {"no":4, "o":None, "title":"4", "isOpen":False, "x":290, "y":167, "w":55,"h":60, "img":oImg["valve"]},
            {"no":5, "o":None, "title":"5", "isOpen":False, "x":350, "y":255, "w":55,"h":60, "img":oImg["valve"]}
        ]
        
        for btn in self.btnList:
            btn["o"] = QPushButton(btn["title"], self)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-image : url("+ btn["img"] +");background-repeat: no-repeat;")
            btn["o"].clicked.connect(partial(self.onBtnClicked, btn["title"], btn["no"]))
        

        # 활성화/비활성화 버튼
        self.btnEnableList = [
            {"no":1, "o":None, "title":"비활성화", "isEnable":False, "x":25, "y":420, "w":75,"h":20},
            {"no":2, "o":None, "title":"비활성화", "isEnable":False, "x":125, "y":420, "w":75,"h":20},
            {"no":3, "o":None, "title":"비활성화", "isEnable":False, "x":225, "y":420, "w":75,"h":20},
            {"no":4, "o":None, "title":"비활성화", "isEnable":False, "x":325, "y":420, "w":75,"h":20},
            {"no":5, "o":None, "title":"비활성화", "isEnable":False, "x":425, "y":420, "w":75,"h":20}
        ]

        for btn in self.btnEnableList:
            btn["o"] = QPushButton(btn["title"], self)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-color : orange;")
            btn["o"].clicked.connect(partial(self.onEnableBtnClicked, btn["no"]))

        # 콤보박스
        self.cbList = [
            {"no":1, "o":None, "title":"", "x":25, "y":450, "w":75,"h":20},
            {"no":2, "o":None, "title":"", "x":125, "y":450, "w":75,"h":20},
            {"no":3, "o":None, "title":"", "x":225, "y":450, "w":75,"h":20},
            {"no":4, "o":None, "title":"", "x":325, "y":450, "w":75,"h":20},
            {"no":5, "o":None, "title":"", "x":425, "y":450, "w":75,"h":20}
        ]
        
        for cb in self.cbList:
            cb["o"] = QComboBox(self)
            cb["o"].addItem("Valve 1")
            cb["o"].addItem("Valve 2")
            cb["o"].addItem("Valve 3")
            cb["o"].addItem("Valve 4")
            cb["o"].addItem("Valve 5")
            cb["o"].move(cb["x"], cb["y"])
            cb["o"].resize(cb["w"], cb["h"])
            cb["o"].currentIndexChanged.connect(partial(self.onCbChanged, cb["no"]))
        
        # 밸브 선택 스핀박스
        self.spboxList = [
            {"no": 1, "o":None, "title":"1", "x":25, "y":475, "w":75,"h":20},
            {"no": 2, "o":None, "title":"2", "x":125, "y":475, "w":75,"h":20},
            {"no": 3, "o":None, "title":"3", "x":225, "y":475, "w":75,"h":20},
            {"no": 4, "o":None, "title":"4", "x":325, "y":475, "w":75,"h":20},
            {"no": 5, "o":None, "title":"5", "x":425, "y":475, "w":75,"h":20}
        ]
        
        for spbox in self.spboxList:
            spbox["o"] = QSpinBox(self)
            spbox["o"].move(spbox["x"], spbox["y"])
            spbox["o"].resize(spbox["w"], spbox["h"])
            spbox["o"].valueChanged.connect(partial(self.onSpboxChanged, spbox["no"]))
    
    # On 콤보박스 index Changed
    def onCbChanged(self, no):
        oCbBox = self.cbList[no-1]["o"]
        print(oCbBox.currentText())

    # On 스핀박스 Value Changed
    def onSpboxChanged(self, no):
        # oSpbox = self.spboxList[no-1]
        # 콤보박스의 중복 체크
        oCbBox = self.cbList[no-1]["o"]
        print(oCbBox.currentText())

    # On 밸브버튼 Clicked
    def onBtnClicked(self, title, no):
        dictBtn = self.btnList[no-1]
        oBtn = dictBtn["o"]
        isOpen = dictBtn["isOpen"]

        color = "red"
        # 열려 있으면, 닫을 거라서, 파->빨 , 빨->파 로 바꿈
        if isOpen:
            color = "red"
        else:
            color = "blue"

        if no == 1:
            self.lineList[1-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 2:
            self.lineList[3-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 3:
            self.lineList[7-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 4:
            self.lineList[2-1]["o"].setStyleSheet("background-color:{};".format(color))
            self.lineList[4-1]["o"].setStyleSheet("background-color:{};".format(color))
            self.lineList[6-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 5:
            self.lineList[10-1]["o"].setStyleSheet("background-color:{};".format(color))

        dictBtn["isOpen"] = not isOpen

    # On 활성화/비활성화 Button Clicked
    def onEnableBtnClicked(self, no):
        oBtn = self.btnEnableList[no-1]["o"]
        isEnable = self.btnEnableList[no-1]["isEnable"]
        if isEnable:
            oBtn.setText("비활성화")
            oBtn.setStyleSheet("background-color : orange;")
            isEnable = False
        elif isEnable == False:
            oBtn.setText("활성화")
            oBtn.setStyleSheet("background-color : green;")
            isEnable = True

    # 매초 call
    def printClock(self):
        strTime = getNow()
        # print(strTime)
        self.lblTime.setText(strTime)
        
        for idx, spbox in enumerate(self.spboxList):
            jBtn = self.btnEnableList[idx]
            oBtn = jBtn["o"]
            strBtn = oBtn.text()
            if strBtn == "활성화":
                oSpbox = spbox["o"]
                spboxNo = int(oSpbox.value())
                if spboxNo > 0:
                    spboxNo = spboxNo -1
                    oSpbox.setValue(spboxNo)

                if spboxNo == 0:
                    oBtn.setText("비활성화")
                    oBtn.setStyleSheet("background-color : orange;")

        # 1초 마다 time tick
        tClock =  threading.Timer(1, self.printClock)
        tClock.daemon = True
        tClock.start()

    # spi 통신결과 받으면,
    def onRecvResult(self, o):
        self.pressure.setText(str(o))

# 현재 시간
def getNow():
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowTitle("Solenoid Valve v0.1 test")
    win.setGeometry(300, 300, 600, 500)
    win.show()

    sys.exit(app.exec_())

    