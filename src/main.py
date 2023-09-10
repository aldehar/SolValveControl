import sys
import datetime
import threading
from functools import partial
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel,QSpinBox, QComboBox, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt

import RPiUtil

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.printClock()

        # 라즈베리파이 관련 인스턴스
        self.rpiUtil = RPiUtil.init(self)

    def initUI(self):
        self.oImg = {
            "on":"res/imgs/on.png",
            "off":"res/imgs/off.png",
            "bg":"res/imgs/printing1.png",
            "valve":"res/imgs/printing2.png",
        }

        self.mainLayout = QVBoxLayout()

        # 상단 - 타이머
        self.lblTime = QLabel("")
        timeFont = self.lblTime.font()
        timeFont.setPointSize(16)
        self.lblTime.setFont(timeFont)
        self.lblTime.setFixedSize(600, 25)
        self.lblTime.setAlignment(Qt.AlignCenter)
        self.mainLayout.addWidget(self.lblTime)

        # 상단 - 자동/수동 전환 버튼
        self.btnOnOff = QPushButton("")
        self.btnOnOff.setFixedSize(100, 40)

        lblMode = QLabel("현재 모드 : ")
        modeFont = lblMode.font()
        modeFont.setBold(True)
        modeFont.setPointSize(16)
        lblMode.setFont(modeFont)

        self.lblMode = QLabel("자동모드")
        self.lblMode.setFont(modeFont)

        self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["on"]))
        self.btnOnOff.clicked.connect(partial(self.onOffBtnClicked))

        self.top2Layout = QHBoxLayout()
        self.top2Layout.addWidget(lblMode)
        self.top2Layout.addWidget(self.lblMode)
        self.top2Layout.addWidget(self.btnOnOff)
        self.mainLayout.addLayout(self.top2Layout)

        self.body = QStackedWidget()
        self.autoPage = QWidget()
        self.manualPage = QWidget()
        self.body.addWidget(self.autoPage)
        self.body.addWidget(self.manualPage)

        ###########################################################################################
        # 자동 레이아웃
        ###########################################################################################

        # 배경
        self.lblBg = QLabel("", self.autoPage)
        self.lblBg.move(0, 15)
        self.lblBg.resize(600, 400)
        self.pixmap = QPixmap()
        self.pixmap.load(self.oImg["bg"])
        self.pixmapVar = self.pixmap.scaledToWidth(600)
        self.lblBg.setPixmap(self.pixmapVar)
        self.lblBg.setStyleSheet("background-color:#e0e0e0;")

        # 압력 게이지
        self.pressure = QLabel("-", self.autoPage)
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
            lblLine["o"] = QLabel("", self.autoPage)
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
            lbl["o"] = QLabel(lbl["title"], self.autoPage)
            lbl["o"].move(lbl["x"], lbl["y"])
            lbl["o"].resize(lbl["w"], lbl["h"])

        # 밸브 버튼(NOP)
        self.btnList = [
            {"no":1, "o":None, "title":"1", "isOpen":False, "x":290, "y":80, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":2, "o":None, "title":"2", "isOpen":False, "x":440, "y":75, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":3, "o":None, "title":"3", "isOpen":False, "x":440, "y":165, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":4, "o":None, "title":"4", "isOpen":False, "x":290, "y":167, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":5, "o":None, "title":"5", "isOpen":False, "x":350, "y":255, "w":55,"h":60, "img":self.oImg["valve"]}
        ]
        
        for btn in self.btnList:
            btn["o"] = QPushButton(btn["title"], self.autoPage)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-image : url("+ btn["img"] +");background-repeat: no-repeat; background-color:red;")
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
            btn["o"] = QPushButton(btn["title"], self.autoPage)
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
            cb["o"] = QComboBox(self.autoPage)
            cb["o"].addItem("Valve 1")
            cb["o"].addItem("Valve 2")
            cb["o"].addItem("Valve 3")
            cb["o"].addItem("Valve 4")
            cb["o"].addItem("Valve 5")
            cb["o"].move(cb["x"], cb["y"])
            cb["o"].resize(cb["w"], cb["h"])
            cb["o"].setCurrentIndex(cb["no"]-1)
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
            spbox["o"] = QSpinBox(self.autoPage)
            spbox["o"].move(spbox["x"], spbox["y"])
            spbox["o"].resize(spbox["w"], spbox["h"])
            spbox["o"].valueChanged.connect(partial(self.onSpboxChanged, spbox["no"]))

        # 밸브 선택 스핀박스
        self.timeLblList = [
            {"no": 1, "o":None, "title":"초", "x":100, "y":475, "w":20,"h":20},
            {"no": 2, "o":None, "title":"초", "x":200, "y":475, "w":20,"h":20},
            {"no": 3, "o":None, "title":"초", "x":300, "y":475, "w":20,"h":20},
            {"no": 4, "o":None, "title":"초", "x":400, "y":475, "w":20,"h":20},
            {"no": 5, "o":None, "title":"초", "x":500, "y":475, "w":20,"h":20}
        ]
        
        for lbl in self.timeLblList:
            lbl["o"] = QLabel(self.autoPage)
            lbl["o"].move(lbl["x"], lbl["y"])
            lbl["o"].resize(lbl["w"], lbl["h"])
            lbl["o"].setText(lbl["title"])
        
        ###########################################################################################
        # 수동 레이아웃
        ###########################################################################################

        # 배경
        self.lblBgManual = QLabel("", self.manualPage)
        self.lblBgManual.move(0, 15)
        self.lblBgManual.resize(600, 400)
        self.pixmapManual = QPixmap()
        self.pixmapManual.load(self.oImg["bg"])
        self.pixmapVarManual = self.pixmapManual.scaledToWidth(600)
        self.lblBgManual.setPixmap(self.pixmapVarManual)
        self.lblBgManual.setStyleSheet("background-color:#e0e0e0;")

        # 압력 게이지
        self.manualPressure = QLabel("-", self.manualPage)
        self.manualPressure.move(235, 215)
        self.manualPressure.resize(250, 50)

        #선
        self.manualLineList = [
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
        
        for lblLine in self.manualLineList:
            lblLine["o"] = QLabel("", self.manualPage)
            lblLine["o"].setText(lblLine["title"])
            lblLine["o"].move(lblLine["x"], lblLine["y"])
            lblLine["o"].resize(lblLine["w"], lblLine["h"])
            lblLine["o"].setStyleSheet("background-color:red;")
        
        # 라벨
        self.manualLabelList = [
            {"no":1, "o":None, "title":"#1 Sol", "x":290, "y":60, "w":55,"h":25},
            {"no":2, "o":None, "title":"#2 Sol", "x":440, "y":55, "w":55,"h":25},
            {"no":3, "o":None, "title":"#3 Sol", "x":440, "y":145, "w":55,"h":25},
            {"no":4, "o":None, "title":"#4 Sol", "x":290, "y":147, "w":55,"h":25},
            {"no":5, "o":None, "title":"#5 Sol", "x":350, "y":235, "w":55,"h":25},
        ]
        
        for lbl in self.manualLabelList:
            lbl["o"] = QLabel(lbl["title"], self.manualPage)
            lbl["o"].move(lbl["x"], lbl["y"])
            lbl["o"].resize(lbl["w"], lbl["h"])

        # 밸브 버튼(NOP)
        self.manualBtnList = [
            {"no":1, "o":None, "title":"1", "isOpen":False, "x":290, "y":80, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":2, "o":None, "title":"2", "isOpen":False, "x":440, "y":75, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":3, "o":None, "title":"3", "isOpen":False, "x":440, "y":165, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":4, "o":None, "title":"4", "isOpen":False, "x":290, "y":167, "w":55,"h":60, "img":self.oImg["valve"]},
            {"no":5, "o":None, "title":"5", "isOpen":False, "x":350, "y":255, "w":55,"h":60, "img":self.oImg["valve"]}
        ]
        
        for btn in self.manualBtnList:
            btn["o"] = QPushButton(btn["title"], self.manualPage)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-image : url("+ btn["img"] +");background-repeat: no-repeat; background-color:red;")
            btn["o"].clicked.connect(partial(self.onBtnClicked, btn["title"], btn["no"]))

        # 레이아웃
        self.mainLayout.addWidget(self.body)
        self.body.setCurrentIndex(0)

        self.mainWidget = QWidget()
        self.mainWidget.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainWidget)

    # On 온/오프 버튼 clicked
    def onOffBtnClicked(self):
        idx = self.body.currentIndex()

        if idx == 0:
            self.lblMode.setText("수동모드")
            self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["off"]))
            self.body.setCurrentIndex(1)
            
        elif idx == 1:
            self.lblMode.setText("자동모드")
            self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["on"]))
            self.body.setCurrentIndex(0)

    # On 콤보박스 index Changed
    def onCbChanged(self, no):
        oCbBox = self.cbList[no-1]["o"]
        print(oCbBox.currentText())
        # @TODO - 콤보박스의 중복 체크

    # On 스핀박스 Value Changed
    def onSpboxChanged(self, no):
        oSpbox = self.spboxList[no-1]

    # On 밸브버튼 Clicked
    def onBtnClicked(self, title, no):
        targetDictBtn = None
        targetIsOpen = False
        targetBtn = None
        targetLineList = None

        # 현재 index가 0이면, 자동, 1이면 수동 
        if self.body.currentIndex() == 0:
            targetDictBtn = self.btnList[no-1]
            targetBtn = targetDictBtn["o"]
            targetLineList = self.lineList
        else:
            targetDictBtn = self.manualBtnList[no-1]
            targetBtn = targetDictBtn["o"]
            targetLineList = self.manualLineList

        targetIsOpen = targetDictBtn["isOpen"]

        color = "red"
        # 열려 있으면, 닫을 거라서, 파->빨 , 빨->파 로 바꿈
        if targetIsOpen:
            color = "red"
        else:
            color = "blue"

        if no == 1:
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(targetDictBtn["img"], color))
            targetLineList[1-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 2:
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(targetDictBtn["img"], color))
            targetLineList[3-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 3:
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(targetDictBtn["img"], color))
            targetLineList[7-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 4:
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(targetDictBtn["img"], color))
            targetLineList[2-1]["o"].setStyleSheet("background-color:{};".format(color))
            targetLineList[4-1]["o"].setStyleSheet("background-color:{};".format(color))
            targetLineList[6-1]["o"].setStyleSheet("background-color:{};".format(color))
        elif no == 5:
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(targetDictBtn["img"], color))
            targetLineList[10-1]["o"].setStyleSheet("background-color:{};".format(color))

        targetDictBtn["isOpen"] = not targetIsOpen

    # On 활성화/비활성화 Button Clicked
    def onEnableBtnClicked(self, no):
        oBtn = self.btnEnableList[no-1]["o"]
        isEnable = self.btnEnableList[no-1]["isEnable"]
        if isEnable:
            oBtn.setText("비활성화")
            oBtn.setStyleSheet("background-color : orange;")
            self.btnEnableList[no-1]["isEnable"] = False
        elif isEnable == False:
            oBtn.setText("활성화")
            oBtn.setStyleSheet("background-color : green;")
            self.btnEnableList[no-1]["isEnable"] = True

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
        self.manualPressure.setText(str(o))

# 현재 시간
def getNow():
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowTitle("Solenoid Valve v0.1 test")
    win.setGeometry(300, 300, 600, 600)
    win.show()

    sys.exit(app.exec_())

    