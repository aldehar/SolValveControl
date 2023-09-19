import sys
import datetime
import threading
import copy
from functools import partial
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel,QSpinBox, QComboBox, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QMessageBox
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt
from PyQt5 import QtCore

import RPiManager

class MainWindow(QMainWindow):
    TAG = "Main"

    def __init__(self):
        super().__init__()
        self.initUI()
        self.setTimer()
        self.setSchedule()

        # 라즈베리파이 관련 인스턴스
        self.rpiUtil = RPiManager.Comm(self)

        # 중복 체크
        for cb in self.cbList:
            cb["o"].currentIndexChanged.connect(partial(self.onCbChanged, cb["no"]))

    # 1초 타이머 세팅
    def setTimer(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.printClock)
        self.timer.start(1000)
        self.printClock()

    # 초기 시간 설정
    def setSchedule(self):
        self.unitFactor = {"h":3600, "m":60, "s":1}

        self.initQueue = [
            {"no":1, "valve":4, "period":"3s", "remain":3, "isSeq":False},
            {"no":2, "valve":1, "period":"2s", "remain":2, "isSeq":True},
            {"no":3, "valve":2, "period":"3s", "remain":3, "isSeq":True},
            {"no":4, "valve":3, "period":"2s", "remain":2, "isSeq":False},
            {"no":5, "valve":5, "period":"4s", "remain":4, "isSeq":False},
        ]

        self.resetQueue(False)

    # 큐 리셋
    def resetQueue(self, isIncludeFirst):
        # 초기 큐의 값만 복사
        self.taskQueue = copy.deepcopy(self.initQueue)

        for dSchedule in self.taskQueue:
            valveNo = int(dSchedule["valve"])
            factor = self.unitFactor[dSchedule["period"][-1:]]
            nTime = int(dSchedule["period"][:-1])
            period = nTime * factor
            idx = dSchedule["no"]-1
            
            self.cbList[idx]["o"].setCurrentIndex(valveNo-1)
            self.cbList[idx]["title"] = str(valveNo)
            self.spboxList[idx]["o"].setValue(int(period))
        
        if not isIncludeFirst:
            # 제일 앞의 것 제거 (활성화시, 제일 처음 밸브가 2번 실행되는 것 방지)
            self.taskQueue.pop(0)
            # 제일 뒤의 것 제거
            self.taskQueue.pop()
            
            print("[{}] resetQueue, {}".format(self.TAG, self.taskQueue))

    # UI 초기화
    def initUI(self):
        self.oImg = {
            "on":"res/imgs/on.png",
            "off":"res/imgs/off.png",
            "bg":"res/imgs/printing1.png",
            "pump":"res/imgs/pump.png",
            "valve_on":"res/imgs/valve_on.png",
            "valve_off":"res/imgs/valve_off.png"
        }

        self.mainLayout = QVBoxLayout()

        # 상단 - 타이머
        self.lblTime = QLabel("")
        timeFont = self.lblTime.font()
        timeFont.setPointSize(16)
        self.lblTime.setFont(timeFont)
        self.lblTime.setFixedSize(250, 40)
        self.lblTime.setAlignment(Qt.AlignCenter)

        # 상단 - 자동/수동 전환 버튼
        self.lblMode = QLabel("자동모드")
        self.lblMode.setFixedSize(220, 40)
        modeFont = self.lblMode.font()
        modeFont.setBold(True)
        modeFont.setPointSize(16)
        self.lblMode.setFont(modeFont)

        self.btnOnOff = QPushButton("")
        self.btnOnOff.setFixedSize(100, 40)
        self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["on"]))
        self.btnOnOff.clicked.connect(partial(self.onOffBtnClicked))

        self.topLayout = QHBoxLayout()
        self.topLayout.setAlignment(Qt.AlignCenter)
        self.topLayout.addWidget(self.lblTime)
        self.topLayout.addWidget(self.lblMode)
        self.topLayout.addWidget(self.btnOnOff)
        self.mainLayout.addLayout(self.topLayout)

        self.body = QStackedWidget()
        self.body.setFixedSize(600,550)
        self.autoPage = QWidget()
        self.manualPage = QWidget()

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
        self.pressure.move(210, 124)
        self.pressure.resize(300, 50)
        
        #선
        self.lineList = [
            {"no":1, "o":None, "title":"1", "x":255, "y":125, "w":85,"h":5},
            {"no":2, "o":None, "title":"2", "x":340, "y":125, "w":125,"h":5},
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
            lblLine["o"].setStyleSheet("background-color:blue;")
        
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

        # 밸브 버튼
        self.btnList = [
            {"no":1, "o":None, "title":"1", "isOpen":False, "x":290, "y":80, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[1]},
            {"no":2, "o":None, "title":"2", "isOpen":False, "x":445, "y":75, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[3]},
            {"no":3, "o":None, "title":"3", "isOpen":False, "x":445, "y":165, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[7]},
            {"no":4, "o":None, "title":"4", "isOpen":False, "x":290, "y":167, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[2, 4, 6]},
            {"no":5, "o":None, "title":"5", "isOpen":False, "x":350, "y":255, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[10]},
            {"no":6, "o":None, "title":"M", "isOpen":False, "x":140, "y":165, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[5, 8, 9]},
            {"no":7, "o":None, "title":"P", "isOpen":False, "x":210, "y":165, "w":60,"h":60, "img":self.oImg["pump"], "lineList":[]}
        ]
        
        for btn in self.btnList:
            btn["o"] = QPushButton(btn["title"], self.autoPage)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-image : url("+ btn["img"] +");background-repeat: no-repeat; background-color:blue;")
            btn["o"].clicked.connect(partial(self.onBtnClicked, btn["no"]))

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
            {"no":1, "o":None, "title":"1", "x":25, "y":450, "w":75,"h":20},
            {"no":2, "o":None, "title":"2", "x":125, "y":450, "w":75,"h":20},
            {"no":3, "o":None, "title":"3", "x":225, "y":450, "w":75,"h":20},
            {"no":4, "o":None, "title":"4", "x":325, "y":450, "w":75,"h":20},
            {"no":5, "o":None, "title":"5", "x":425, "y":450, "w":75,"h":20}
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
            #cb["o"].setCurrentIndex(int(cb["title"])-1)
        
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

        # 밸브 초 라벨
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
        self.manualPressure.move(210, 124)
        self.manualPressure.resize(300, 50)

        #선
        self.manualLineList = [
            {"no":1, "o":None, "title":"1", "x":255, "y":125, "w":85,"h":5},
            {"no":2, "o":None, "title":"2", "x":340, "y":125, "w":125,"h":5},
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
            lblLine["o"].setStyleSheet("background-color:blue;")
        
        # 라벨
        self.manualLabelList = [
            {"no":1, "o":None, "title":"#1 Sol", "x":290, "y":60, "w":55,"h":25},
            {"no":2, "o":None, "title":"#2 Sol", "x":440, "y":55, "w":55,"h":25},
            {"no":3, "o":None, "title":"#3 Sol", "x":440, "y":145, "w":55,"h":25},
            {"no":4, "o":None, "title":"#4 Sol", "x":290, "y":147, "w":55,"h":25},
            {"no":5, "o":None, "title":"#5 Sol", "x":350, "y":235, "w":55,"h":25}
        ]
        
        for lbl in self.manualLabelList:
            lbl["o"] = QLabel(lbl["title"], self.manualPage)
            lbl["o"].move(lbl["x"], lbl["y"])
            lbl["o"].resize(lbl["w"], lbl["h"])

        # 밸브 버튼
        self.manualBtnList = [
            {"no":1, "o":None, "title":"1", "isOpen":False, "x":290, "y":80, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[1]},
            {"no":2, "o":None, "title":"2", "isOpen":False, "x":445, "y":75, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[3]},
            {"no":3, "o":None, "title":"3", "isOpen":False, "x":445, "y":165, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[7]},
            {"no":4, "o":None, "title":"4", "isOpen":False, "x":290, "y":167, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[2, 4, 6]},
            {"no":5, "o":None, "title":"5", "isOpen":False, "x":350, "y":255, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[10]},
            {"no":6, "o":None, "title":"M", "isOpen":False, "x":140, "y":165, "w":51,"h":60, "img":self.oImg["valve_off"], "lineList":[5, 8, 9]},
            {"no":7, "o":None, "title":"P", "isOpen":False, "x":210, "y":165, "w":60,"h":60, "img":self.oImg["pump"], "lineList":[]}
        ]
        
        for btn in self.manualBtnList:
            btn["o"] = QPushButton(btn["title"], self.manualPage)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(btn["img"]))
            btn["o"].clicked.connect(partial(self.onBtnClicked, btn["no"]))

        # 레이아웃
        self.body.addWidget(self.autoPage)
        self.body.addWidget(self.manualPage)
        self.body.setCurrentIndex(0)

        self.mainLayout.addWidget(self.body)
        self.mainLayout.setAlignment(Qt.AlignCenter)
        
        self.mainWidget = QWidget()
        self.mainWidget.setLayout(self.mainLayout)

        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.mainWidget)
        self.setCentralWidget(self.scroll)

    # On 온/오프 버튼 clicked
    def onOffBtnClicked(self):
        idx = self.body.currentIndex()

        # 자동모드 -> 수동모드
        if idx == 0:
            self.lblMode.setText("수동모드")
            self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["off"]))
            self.body.setCurrentIndex(1)

            # 자동모드 -> 수동모드 전환 시, 모든 밸브 정지
            for o in self.btnList:
                self.rpiUtil.setOutput(no=o["no"], isHigh=False)
                o["isOpen"] = False

                no = int(o["no"])
                if no != 7:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["valve_off"]))
                else:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["pump"]))

            # 활성화 버튼 -> 비활성화로
            for o in self.btnEnableList:
                o["o"].setText("비활성화")
                o["o"].setStyleSheet("background-color:orange;")
                o["title"] = "비활성화"
            
            # 라인 off 색으로
            for o in self.lineList:
                o["o"].setStyleSheet("background-color:{};".format("blue"))

        # 수동모드 -> 자동모드
        elif idx == 1:
            self.lblMode.setText("자동모드")
            self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["on"]))
            self.body.setCurrentIndex(0)

    # On 콤보박스 index Changed
    def onCbChanged(self, no):
        oCbBox = self.cbList[no-1]["o"]
        newStr = oCbBox.currentText()

        # @TODO - 콤보박스의 중복 체크
        isFound = False
        for dictCb in self.cbList:
            searchingNo = dictCb["no"]-1
            # 현재 no가 아니라면, (다른 cb의 no)
            if no != searchingNo:
                otherText = dictCb["o"].currentText()
                print("[{}]>> 중복 {} ===> {}".format(self.TAG, otherText, newStr))
                if newStr == otherText:
                    #print("[{}] 중복".format(self.TAG))
                    isFound = True
                    break

        if isFound:
            # QMessageBox.warning(self,'경고','밸브가 중복됩니다.')
            pass
        
        self.cbList[no-1]["title"] = self.cbList[no-1]["o"].currentIndex()+1

    # On 스핀박스 Value Changed
    def onSpboxChanged(self, no):
        oSpbox = self.spboxList[no-1]

    # On 밸브버튼 Clicked
    def onBtnClicked(self, no):
        if no != 6:
            self.printLine(no)
        
        # 자동모드 일때만,
        if self.body.currentIndex() == 0:
            # 모터 버튼 클릭 시,(임시)
            if no == 6:
                self.resetQueue(True)
                self.nextValve(no)
            # 압력계 버튼 클릭 시,(임시)
            elif no == 7:
                self.resetQueue(False)

    # 배관 선 색깔 표시
    def printLine(self, no):
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
        
        color = "blue"
        strImg = "valve_off"
        # 열려 있으면, 닫을 거라서, 파->빨 , 빨->파 로 바꿈
        if targetIsOpen:
            color = "blue"
            strImg = "valve_off"
        else:
            color = "red"
            strImg = "valve_on"

        if no == 7:
            strImg = "pump"

        # 대상에 한해서(밸브5, 모터1, 압력계)
        if no >= 1 and no <= 7:
            # 버튼 색깔 및 배경 변경
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(self.oImg[strImg], color))
            # 줄색깔 변경
            lineList = targetDictBtn["lineList"]
            for no in lineList:
                targetLineList[no-1]["o"].setStyleSheet("background-color:{};".format(color))
            # 켜고 끄기(밸브5, 모터1)
            if no >= 1 and no <= 6:
                self.rpiUtil.setOutput(no, not targetIsOpen)

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
        
        cbIdx = int(self.cbList[no-1]["o"].currentText()[-1:])
        self.printLine(cbIdx)

    # 매초 call
    def printClock(self):
        strTime = getNow()
        self.lblTime.setText(strTime)
        
        self.checkBtnActive()

    # 활성화/비활성화 버튼 체크
    def checkBtnActive(self):
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
                    valveNo = int(self.cbList[idx]["o"].currentText()[-1:])
                    # 현재 밸브 처리(GUI-선색깔, GPIO)
                    self.printLine(valveNo)
                    # 0초 되면, 다음걸로 넘어가기
                    self.nextValve(valveNo)

    # 다음 밸브처리
    def nextValve(self, valveNo):
        if valveNo == 4:
            self.printLine(5)
        elif valveNo == 5:
            self.printLine(4)
        
        print("[{}] taskQueue : {}".format(self.TAG, self.taskQueue))
        # task 큐에 남아있다면, 
        if len(self.taskQueue) > 0:
            # 큐에서 하나를 꺼내서,
            nowTask = self.taskQueue.pop(0)
            valveNo = int(nowTask["valve"])
            factor = self.unitFactor[nowTask["period"][-1:]]
            # 시간(초)
            nTime = int(nowTask["period"][:-1]) * factor
            
            # 콤보박스의 번호 0 ~ 4
            idx = nowTask["no"]-1

            self.spboxList[idx]["o"].setValue(int(nTime))
            self.cbList[idx]["title"] = "Valve {}".format(valveNo)
            self.btnEnableList[idx]["o"].setText("활성화")
            self.btnEnableList[idx]["o"].setStyleSheet("background-color : green;")
            self.printLine(valveNo)

            '''
            isSeq = nowTask["isSeq"]
            if isSeq == True:
                self.nextValve()
            '''
        else:
            self.resetQueue(False)
            # 모터 토글
            self.printLine(6)

    # spi 통신결과 받으면,
    def onRecvResult(self, o):
        # for debug
        print("[{}] SPI >>> {}".format(self.TAG, str(o)))
        self.pressure.setText(str(o))
        self.manualPressure.setText(str(o))

    def closeEvent(self, event):
        print("[{}] close window...".format(self.TAG))
        # 라즈베리파이 자원 해제
        self.rpiUtil.release()
        event.accept()

# 현재 시간
def getNow():
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowTitle("Solenoid Valve v0.1 test")
    win.setGeometry(300, 300, 625, 575)
    win.show()

    sys.exit(app.exec_())

    