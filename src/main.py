import sys
import datetime
import threading
import copy
from functools import partial
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel,QSpinBox, QComboBox, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QMessageBox, QDesktopWidget, QLineEdit
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QObject, pyqtSlot, pyqtSignal, QThread, QTimer, QSettings
from PyQt5 import QtCore

import RPiManager
import log as Log

class MainWindow(QMainWindow):
    TAG = "Main"
    oIdxName = {"MODE_AUTO":0, "MODE_MANUAL":1, "Valve1":1, "Valve2":2, "Valve3":3, "Valve4":4, "Valve5":5, "Motor":6, "Dog_Feed":7}
    
    oDogFeed = {
        "isRunning" : False,
        "feedTime" : 45
    }
    
    # 설정파일(config.ini)에서 파일을 못읽어왓을때 기본값
    startPressure = 1.0

    dogFeedTimer = None

    def __init__(self):
        """생성자
        """
        super().__init__()
        self.initUI()
        self.setSchedule()

        # 라즈베리파이 관련 인스턴스
        self.rpiUtil = RPiManager.Comm(self)
        self.rpiUtil.sigMeasurePressure.connect(self.onRecvResult)

        self.timeWorker = TimeWorker()
        self.timeWorker.timeout.connect(self.sigTimeout)
        self.timeWorker.isRunning = True
        self.timeWorker.start()

        # 중복 체크(UI세팅시에 넣으면, 초기 값 세팅시에 체크됨)
        for cb in self.cbList:
            cb["o"].currentIndexChanged.connect(partial(self.onCbChanged, cb["no"]))

    # ini 파일에서 세팅값 읽어오기
    def loadSetting(self):
        oSetting = {
            "isCorrect" : False
        }

        try:
            self.settings = QSettings("config.ini", QSettings.IniFormat)
            strSeq = self.settings.value("SETTING/Sequence")
            oSetting["valve1"] = self.settings.value("SETTING/valve1")
            oSetting["valve2"] = self.settings.value("SETTING/valve2")
            oSetting["valve3"] = self.settings.value("SETTING/valve3")
            oSetting["valve5"] = self.settings.value("SETTING/valve5")
            oSetting["feedTime"] = self.settings.value("SETTING/feed_time")
            # 개밥 시간
            self.oDogFeed["feedTime"] = self.parseTime(oSetting["feedTime"])
            self.spDogFeedTime.setValue(self.oDogFeed["feedTime"])
            # 동작압력
            self.startPressure = float(self.settings.value("SETTING/pressure"))
            self.edPressure.setText(str(self.startPressure))

            if strSeq.find("0") >= 0:
                oSetting["isCorrect"] = False
            else:
                oSetting["Sequence"] = strSeq
                oSetting["isCorrect"] = True

        except Exception as e:
            Log.e(self.TAG, str(e))

        return oSetting
    
    # 초기 스케쥴 시간 설정
    def setSchedule(self):
        """초기 스케쥴 시간 설정
            @TODO ini 파일에서 읽어오기?
        """
        self.unitFactor = {"h":3600, "m":60, "s":1}

        oSetting = self.loadSetting()
        Log.d(self.TAG, "설정에서 불러온 값 : {}".format(oSetting))

        if oSetting["isCorrect"]:
            # 설정 파일 불러오기 성공 시,
            self.initQueue = []

            strSeqList = oSetting["Sequence"]
            seqList = strSeqList.split(",")
            tempList = []
            for idx, valveNo in enumerate(seqList):
                o = {
                    "no" : idx + 1,
                    "valve":valveNo
                }
                tempList.append(o)

            no = 1
            try:

                for o in tempList:
                    o["no"] = no
                    o["period"] = oSetting["valve"+o["valve"]]
                    o["remain"] = self.parseTime(o["period"])
                    no = no + 1

                self.initQueue = self.initQueue + tempList
                Log.d(self.TAG, "설정에서 불러온 initQueue 값 : {}".format(self.initQueue))
            except Exception as e:
                errMsg = "저장된 세팅 불러오기 중 오류가 발생되었습니다. 사유 : {}".format(e)
                Log.e(self.TAG, errMsg)
                QMessageBox.critical(self, "저장된 세팅 불러오기 오류", "{}\n 'config.ini' 파일을 확인해보세요.".format(errMsg))
        else:
            # 설정파일 불러오기 실패 시,
            self.initQueue = [
                {"no":1, "valve":1, "period":"8s", "remain":8},
                {"no":2, "valve":2, "period":"6s", "remain":6},
                {"no":3, "valve":3, "period":"7s", "remain":7},
                {"no":4, "valve":5, "period":"5s", "remain":5}
            ]

        self.resetQueue()
        self.isTaskRunning = False

    # 시간 파싱
    def parseTime(self, strTime):
        """시간 파싱

        Args:
            strTime (string): ex> 12h 34m 56s

        Returns:
            int: calculated sec
        """
        factorList = [
            {"unit":"h", "factor":3600},
            {"unit":"m", "factor":60},
            {"unit":"s", "factor":1},
        ]

        totalTime = 0
        idx = 0
        for o in factorList:
            try:
                # h, m, s
                nn = strTime.index(o["unit"])
                # 00~99
                n = int(strTime[idx:nn])
                # 
                nTime = n * o["factor"]
                totalTime = totalTime + nTime
                # unit(h,m,s) 뒤 부터 파싱
                idx = nn + 1
            except Exception as e:
                #Log.d(self.TAG, "==> parseTime() Exception cause : {} ,maybe factor unit not exist in string => s = {} , o = {}".format(e, strTime, o))
                pass
        
        return totalTime

    # 큐 리셋
    def resetQueue(self):
        """큐 리셋
        """
        Log.d(self.TAG, "resetQueue()")
        # 초기 큐의 값만 복사
        self.taskQueue = copy.deepcopy(self.initQueue)
        self.taskNoticeQueue = copy.deepcopy(self.taskQueue)

        for dSchedule in self.taskQueue:
            valveNo = int(dSchedule["valve"])
            factor = self.unitFactor[dSchedule["period"][-1:]]
            nTime = int(dSchedule["period"][:-1])
            period = nTime * factor
            idx = dSchedule["no"]-1
            
            if valveNo == self.oIdxName["Valve5"]:
                # 4번 밸브가 콤보박스에서 빠졌기때문에 Vavle1,2,3,5 라서 5번인 경우, index가 3임
                self.cbList[idx]["o"].setCurrentIndex(valveNo-2)
            else:
                self.cbList[idx]["o"].setCurrentIndex(valveNo-1)

            self.cbList[idx]["title"] = str(valveNo)
            self.spboxList[idx]["o"].setValue(int(period))

        Log.d(self.TAG, "Queue - {}".format(self.taskQueue))

    def moveToCenter(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # UI 초기화
    def initUI(self):
        """UI 초기화
        """
        self.oImg = {
            "on":"res/imgs/on.png",
            "off":"res/imgs/off.png",
            "bg":"res/imgs/printing1.png",
            "pump_on":"res/imgs/pump_on.png",
            "pump_off":"res/imgs/pump_off.png",
            "valve_on":"res/imgs/valve_on.png",
            "valve_off":"res/imgs/valve_off.png",
            "dog_feed_on":"res/imgs/dog_feed_on.png",
            "dog_feed_off":"res/imgs/dog_feed_off.png"
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
        self.lblBg.resize(600, 350)
        self.pixmap = QPixmap()
        self.pixmap.load(self.oImg["bg"])
        self.pixmapVar = self.pixmap.scaledToWidth(600)
        self.lblBg.setPixmap(self.pixmapVar)
        self.lblBg.setStyleSheet("background-color:#e0e0e0;")

        # 압력 게이지
        self.pressure = QLabel("-", self.autoPage)
        self.pressure.move(210, 124)
        self.pressure.resize(300, 50)
        
        #선 - 왼쪽위에서 부터 1~10
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
            {"no":10, "o":None, "title":"10", "x":400, "y":283, "w":145,"h":5}
        ]
        
        for lblLine in self.lineList:
            lblLine["o"] = QLabel("", self.autoPage)
            #lblLine["o"].setText(lblLine["title"])
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
            {"no":6, "o":None, "title":"M", "isOpen":False, "x":140, "y":165, "w":51,"h":60, "img":self.oImg["pump_off"], "lineList":[5, 8, 9]},
            {"no":7, "o":None, "title":"", "isOpen":False, "x":50, "y":250, "w":90,"h":60, "img":self.oImg["dog_feed_off"], "lineList":[]}
        ]
        
        for btn in self.btnList:
            btn["o"] = QPushButton(btn["title"], self.autoPage)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            btn["o"].setStyleSheet("background-image : url("+ btn["img"] +");background-repeat: no-repeat; background-color:blue;")
            btn["o"].clicked.connect(partial(self.onBtnClicked, btn["no"]))

        # 활성화/비활성화 버튼
        self.btnEnableList = [
            {"no":1, "o":None, "title":"비활성화", "isEnable":False, "x":25, "y":360, "w":90,"h":20},
            {"no":2, "o":None, "title":"비활성화", "isEnable":False, "x":125, "y":360, "w":90,"h":20},
            {"no":3, "o":None, "title":"비활성화", "isEnable":False, "x":225, "y":360, "w":90,"h":20},
            {"no":4, "o":None, "title":"비활성화", "isEnable":False, "x":325, "y":360, "w":90,"h":20},
            {"no":5, "o":None, "title":"비활성화", "isEnable":False, "x":425, "y":360, "w":90,"h":20}
        ]

        for btn in self.btnEnableList:
            btn["o"] = QPushButton(btn["title"], self.autoPage)
            btn["o"].move(btn["x"], btn["y"])
            btn["o"].resize(btn["w"], btn["h"])
            # 비활성화 처리
            btn["o"].setEnabled(False)
            btn["o"].setStyleSheet("background-color : orange; color:black;")
            #btn["o"].clicked.connect(partial(self.onEnableBtnClicked, btn["no"]))

        # 4번 밸브
        lbValve4 = QLabel(self.autoPage)
        lbValve4.setText("Valve 4")
        lbValve4.setStyleSheet("background-color :#e1e1e1; border: 1px solid #adadad;")
        lbValve4.setAlignment(Qt.AlignCenter)
        lbValve4.move(25, 390)
        lbValve4.resize(90, 25)

        # 시간설정 버튼
        self.btnSetTime = QPushButton(self.autoPage)
        self.btnSetTime.setText("시간 저장")
        self.btnSetTime.move(25, 420)
        self.btnSetTime.resize(90, 25)
        self.btnSetTime.clicked.connect(self.onBtnClicked)

        # 콤보박스 - 밸브선택
        self.cbList = [
            {"no":1, "o":None, "title":"2", "x":125, "y":390, "w":90,"h":25},
            {"no":2, "o":None, "title":"3", "x":225, "y":390, "w":90,"h":25},
            {"no":3, "o":None, "title":"4", "x":325, "y":390, "w":90,"h":25},
            {"no":4, "o":None, "title":"5", "x":425, "y":390, "w":90,"h":25}
        ]
        
        for cb in self.cbList:
            cb["o"] = QComboBox(self.autoPage)
            cb["o"].addItem("Valve 1")
            cb["o"].addItem("Valve 2")
            cb["o"].addItem("Valve 3")
            cb["o"].addItem("Valve 5")
                
            cb["o"].move(cb["x"], cb["y"])
            cb["o"].resize(cb["w"], cb["h"])
            #cb["o"].setCurrentIndex(cb["no"]-1)
        
        # 밸브 초 값 스핀박스
        self.spboxList = [
            {"no": 1, "o":None, "title":"2", "x":125, "y":420, "w":75,"h":25, "isHidden":False},
            {"no": 2, "o":None, "title":"3", "x":225, "y":420, "w":75,"h":25, "isHidden":False},
            {"no": 3, "o":None, "title":"4", "x":325, "y":420, "w":75,"h":25, "isHidden":False},
            {"no": 4, "o":None, "title":"5", "x":425, "y":420, "w":75,"h":25, "isHidden":False}
        ]
        
        for spbox in self.spboxList:
            spbox["o"] = QSpinBox(self.autoPage)
            spbox["o"].move(spbox["x"], spbox["y"])
            spbox["o"].resize(spbox["w"], spbox["h"])
            # 최대 3시간
            spbox["o"].setRange(0, 3600*3)
            spbox["o"].valueChanged.connect(partial(self.onSpboxChanged, spbox["no"]))
            if spbox["isHidden"]:
                spbox["o"].hide()

        # 밸브 초 라벨
        self.timeLblList = [
            {"no": 1, "o":None, "title":"초", "x":105, "y":425, "w":20,"h":20, "isHidden":True},
            {"no": 2, "o":None, "title":"초", "x":205, "y":425, "w":20,"h":20, "isHidden":False},
            {"no": 3, "o":None, "title":"초", "x":305, "y":425, "w":20,"h":20, "isHidden":False},
            {"no": 4, "o":None, "title":"초", "x":405, "y":425, "w":20,"h":20, "isHidden":False},
            {"no": 5, "o":None, "title":"초", "x":505, "y":425, "w":20,"h":20, "isHidden":False}
        ]
        
        for lbl in self.timeLblList:
            lbl["o"] = QLabel(self.autoPage)
            lbl["o"].move(lbl["x"], lbl["y"])
            lbl["o"].resize(lbl["w"], lbl["h"])
            lbl["o"].setText(lbl["title"])
            if lbl["isHidden"]:
                lbl["o"].hide()
        
        # 동작 압력 설정
        lblSetPressure = QLabel(self.autoPage)
        lblSetPressure.setText("동작 압력")
        lblSetPressure.move(525, 365)

        self.edPressure = QLineEdit(self.autoPage)
        self.edPressure.move(525, 390)
        self.edPressure.setText(str(self.startPressure))
        self.edPressure.resize(30, 25)

        lblBar = QLabel(self.autoPage)
        lblBar.setText("bar")
        lblBar.move(560, 400)

        self.btnSetPressure = QPushButton(self.autoPage, text="압력 설정")
        self.btnSetPressure.move(525, 420)
        self.btnSetPressure.resize(70, 25)
        self.btnSetPressure.clicked.connect(self.setPressure)

        # 개밥주기 시간
        self.spDogFeedTime = QSpinBox(self.autoPage)
        self.spDogFeedTime.move(50, 310)
        self.spDogFeedTime.resize(90, 25)
        self.spDogFeedTime.setRange(0, 9999)
        self.spDogFeedTime.setValue(int(self.oDogFeed["feedTime"]))
        
        ###########################################################################################
        # 수동 레이아웃
        ###########################################################################################

        # 배경
        self.lblBgManual = QLabel("", self.manualPage)
        self.lblBgManual.move(0, 15)
        self.lblBgManual.resize(600, 350)
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
            {"no":10, "o":None, "title":"10", "x":400, "y":283, "w":145,"h":5}
        ]
        
        for lblLine in self.manualLineList:
            lblLine["o"] = QLabel("", self.manualPage)
            #lblLine["o"].setText(lblLine["title"])
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
            {"no":7, "o":None, "title":"", "isOpen":False, "x":50, "y":250, "w":90,"h":60, "img":self.oImg["dog_feed_off"], "lineList":[]}
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
        """온/오프 버튼 클릭 시, callback
        """
        idx = self.body.currentIndex()

        # 자동모드 -> 수동모드
        if idx == self.oIdxName["MODE_AUTO"]:
            # 밸브 열기/닫기 시퀀스 정지
            self.isTaskRunning = False
            # 개밥 타이머 정지
            self.oDogFeed["isRunning"] = False
            if self.dogFeedTimer != None:
                self.dogFeedTimer.stop()

            self.lblMode.setText("수동모드")
            self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["off"]))
            self.body.setCurrentIndex(self.oIdxName["MODE_MANUAL"])

            # 자동모드 -> 수동모드 전환 시, 모든 밸브 정지
            for o in self.btnList:
                self.rpiUtil.setOutput(no=o["no"], isHigh=False)
                o["isOpen"] = False

                no = int(o["no"])
                if no == self.oIdxName["Motor"]:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["pump_off"]))
                elif no == self.oIdxName["Dog_Feed"]:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["dog_feed_off"]))
                else:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["valve_off"]))

            # 활성화 버튼 -> 비활성화로
            for o in self.btnEnableList:
                o["o"].setText("비활성화")
                o["o"].setStyleSheet("background-color:orange; color:black;")
                o["title"] = "비활성화"
            
            # 라인 off 색으로
            for o in self.lineList:
                o["o"].setStyleSheet("background-color:{};".format("blue"))

            # 큐 초기화
            self.resetQueue()

        # 수동모드 -> 자동모드
        elif idx == self.oIdxName["MODE_MANUAL"]:
            for o in self.manualBtnList:
                # 전환 시, 모든 밸브 off
                self.rpiUtil.setOutput(no=o["no"], isHigh=False)
                o["isOpen"] = False

                no = int(o["no"])
                if no == self.oIdxName["Motor"]:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["pump_off"]))
                elif no == self.oIdxName["Dog_Feed"]:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["dog_feed_off"]))
                else:
                    o["o"].setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:blue;".format(self.oImg["valve_off"]))

            # 선 모두 꺼짐(파란색)으로 처리
            for o in self.manualLineList:
                o["o"].setStyleSheet("background-color:{};".format('blue'))

            self.spDogFeedTime.setValue(self.oDogFeed["feedTime"])

            self.lblMode.setText("자동모드")
            self.btnOnOff.setStyleSheet("background-image : url({});background-repeat: no-repeat;".format(self.oImg["on"]))
            self.body.setCurrentIndex(self.oIdxName["MODE_AUTO"])
            
    # On 콤보박스 index Changed
    def onCbChanged(self, no):
        """콤보박스 index 변화시에, callback

        Args:
            no (int): 번호
        """
        oCbBox = self.cbList[no-1]["o"]
        newStr = oCbBox.currentText()

        # @TODO - 콤보박스의 중복 체크
        isFound = False
        for dictCb in self.cbList:
            searchingNo = dictCb["no"]-1
            # 현재 no가 아니라면, (다른 cb의 no)
            if no != searchingNo:
                otherText = dictCb["o"].currentText()
                Log.d(self.TAG, ">> 중복 {} ===> {}".format(otherText, newStr))
                if newStr == otherText:
                    isFound = True
                    break

        if isFound:
            # QMessageBox.warning(self,'경고','밸브가 중복됩니다.')
            pass
        
        self.cbList[no-1]["title"] = self.cbList[no-1]["o"].currentIndex()+1

    # On 스핀박스 Value Changed
    def onSpboxChanged(self, no):
        """스핀박스 값 변화시, callback

        Args:
            no (int): 번호
        """
        oSpbox = self.spboxList[no-1]

    # On 밸브버튼 Clicked
    def onBtnClicked(self, no):
        """밸브버튼 클릭시, callback

        Args:
            no (int): 버튼 번호
        """

        # 시간 저장
        if self.sender() == self.btnSetTime:
            self.saveSetting()
            return

        bodyIndex = self.body.currentIndex()

        # 자동모드 일때만,
        if bodyIndex == self.oIdxName["MODE_AUTO"]:
            if no == self.oIdxName["Dog_Feed"]:
                if self.oDogFeed["isRunning"] == False:
                    Log.d(self.TAG, "[Start] 개밥주기")
                    self.oDogFeed["isRunning"] = True
                    # 버튼 색깔 처리
                    self.printLine(no)
                    self.rpiOut(no, self.btnList[no-1]["isOpen"])

                    dogFeedTime = self.spDogFeedTime.value()
                    self.oDogFeed["feedTime"] = dogFeedTime
                    Log.i(self.TAG, "개밥 시간 : {}".format(dogFeedTime))

                    self.dogFeedTimer = QTimer(self)
                    self.dogFeedTimer.start(int(dogFeedTime) * 1000)
                    self.dogFeedTimer.setSingleShot(True)
                    self.dogFeedTimer.timeout.connect(self.onTimeout)
                else:
                    Log.d(self.TAG, "이미 개밥 주는 중...")
            else:
                self.startTask(no)

        # 수동모드 일때만,
        elif bodyIndex == self.oIdxName["MODE_MANUAL"]:
            # 자기 밸브 처리
            isOpen = self.manualBtnList[no-1]["isOpen"]
            # toggle
            self.rpiOut(no, not isOpen)
            self.printLine(no)

            # 4,5번 밸브의 경우, 서로 끄게 처리
            if no == self.oIdxName["Valve4"]:
                isOpen5 = self.manualBtnList[self.oIdxName["Valve5"]-1]["isOpen"]
                if isOpen5:
                    self.printLine(self.oIdxName["Valve5"])
                self.rpiOut(self.oIdxName["Valve5"], isOpen=False)
            elif no == self.oIdxName["Valve5"]:
                isOpen4 = self.manualBtnList[self.oIdxName["Valve4"]-1]["isOpen"]
                if isOpen4:
                    self.printLine(self.oIdxName["Valve4"])
                self.rpiOut(self.oIdxName["Valve4"], isOpen=False)
    
    def onTimeout(self):
        sender = self.sender()
        if sender == self.dogFeedTimer:
            Log.d(self.TAG, "[End] 개밥주기")
            # 버튼 색깔 처리
            no = self.oIdxName["Dog_Feed"]
            self.printLine(no)
            self.rpiOut(no, self.btnList[no-1]["isOpen"])
            self.oDogFeed["isRunning"] = False
            self.spDogFeedTime.setValue(self.oDogFeed["feedTime"])

    # 자동모드 시작
    def startTask(self, no):
        """자동모드 시작

        Args:
            no (int): 밸브 번호
        """
        Log.d(self.TAG, "startTask() No : {}".format(no))

        # 작업 동작중 일때는 끝날때까지 안되게 수정
        if self.isTaskRunning:
            Log.w(self.TAG, ">> 이미 작업 중 입니다.")
            return
        
        self.saveTime()

        # 모터 버튼 클릭 시,(임시)
        if no == self.oIdxName["Motor"]:
            self.isTaskRunning = True
            self.printLine(no)
            self.nextValve(no)

    # 시간 저장
    def saveTime(self):
        """콤보박스의 시간 저장
        """
        # 작업 큐 초기화
        self.taskQueue.clear()
        self.taskNoticeQueue.clear()

        # 콤보박스의 값을 작업 큐에 넣기
        for idx, cb in enumerate(self.cbList):
            oCb = cb["o"]
            cbIdx = oCb.currentIndex()
            # 현재 스핀박스의 값 가져오기
            vSp = self.spboxList[idx]["o"].value()

            oTemp = {}
            oTemp["no"] = cb["no"]

            if (cbIdx + 1) == self.oIdxName["Valve4"]:
                oTemp["valve"] = self.oIdxName["Valve5"]
            else:
                oTemp["valve"] = cbIdx + 1

            oTemp["period"] = str(vSp) + "s"
            
            self.taskQueue.append(oTemp)
        
        # 초기 큐 값을 현재의 큐 값으로 세팅(1사이클 돌아도 세팅된 값으로 저장되게함)
        self.initQueue.clear()
        self.initQueue = copy.deepcopy(self.taskQueue)
        self.taskNoticeQueue = copy.deepcopy(self.taskQueue)

    # 배관 선 색깔 표시
    def printLine(self, no):
        """배관 선 색깔 표시

        Args:
            no (int): 버튼 번호
        """
        targetDictBtn = None
        targetIsOpen = False
        targetBtn = None
        targetLineList = None

        # 현재 index가 0이면, 자동, 1이면 수동 
        if self.body.currentIndex() == self.oIdxName["MODE_AUTO"]:
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
            if no == self.oIdxName["Motor"]:
                strImg = "pump_off"
            elif no == self.oIdxName["Dog_Feed"]:
                strImg = "dog_feed_off"
            else:
                strImg = "valve_off"
        else:
            color = "red"
            if no == self.oIdxName["Motor"]:
                strImg = "pump_on"
            elif no == self.oIdxName["Dog_Feed"]:
                strImg = "dog_feed_on"
            else:
                strImg = "valve_on"

        # 대상에 한해서(밸브5, 모터1)
        if no >= self.oIdxName["Valve1"] and no <= self.oIdxName["Dog_Feed"]:
            # 버튼 색깔 및 배경 변경
            targetBtn.setStyleSheet("background-image : url({});background-repeat: no-repeat; background-color:{};".format(self.oImg[strImg], color))
            # 줄색깔 변경
            lineList = targetDictBtn["lineList"]
            for no in lineList:
                targetLineList[no-1]["o"].setStyleSheet("background-color:{};".format(color))
        
        targetDictBtn["isOpen"] = not targetIsOpen

    # 라즈베리 파이 출력
    def rpiOut(self, no, isOpen):
        """라즈베리 파이 출력

        Args:
            no (int): 버튼 번호 = 1~5-밸브, 6-모터, 7-압력계 
            isOpen (boolean): 열렸는지?
        """
        Log.d(self.TAG, "RPi Out - No : {}, IsOpen : {}".format(no, isOpen))
        # 켜고 끄기(밸브5, 모터1)
        if no >= self.oIdxName["Valve1"] and no <= self.oIdxName["Dog_Feed"]:
            self.rpiUtil.setOutput(no, isOpen)

    # On 활성화/비활성화 Button Clicked(더 이상 안씀)
    def onEnableBtnClicked(self, no):
        """On 활성화/비활성화 Button Clicked callback(더 이상 안씀)

        Args:
            no (int): 번호
        """
        oBtn = self.btnEnableList[no-1]["o"]
        isEnable = self.btnEnableList[no-1]["isEnable"]
        if isEnable:
            oBtn.setText("비활성화")
            oBtn.setStyleSheet("background-color : orange; color:black;")
            self.btnEnableList[no-1]["isEnable"] = False
        elif isEnable == False:
            oBtn.setText("활성화")
            oBtn.setStyleSheet("background-color : green; color:black;")
            self.btnEnableList[no-1]["isEnable"] = True
        
        cbIdx = int(self.cbList[no-1]["o"].currentText()[-1:])
        self.printLine(cbIdx)
        self.rpiOut(cbIdx+1, isEnable)

    # 활성화/비활성화 버튼 체크
    def checkBtnActive(self):
        """활성화/비활성화 버튼 체크
        """
        for btnIdx, dBtn in enumerate(self.btnEnableList):
            # 0번 활성화 버튼 4번 밸브 버튼, 4번은 combobox, spinbox가 없다.
            if btnIdx != 0:
                spIdx = btnIdx -1
                spbox = self.spboxList[spIdx]
                oBtn = dBtn["o"]
                strBtn = oBtn.text()
                if strBtn == "활성화":
                    valveNo = int(self.cbList[spIdx]["o"].currentText()[-1:])
                    oSpbox = spbox["o"]
                    spboxValue = int(oSpbox.value())
                    if spboxValue > 0:
                        spboxValue = spboxValue -1
                        oSpbox.setValue(spboxValue)
                        # 남은 시간 저장하게 매초 넣게 수정
                        nowValveIdx = -1
                        if valveNo >= self.oIdxName["Valve1"] and valveNo <= self.oIdxName["Valve3"]:
                            nowValveIdx = spIdx - 1
                        elif valveNo == self.oIdxName["Valve5"]:
                            nowValveIdx = 3
                        self.taskNoticeQueue[nowValveIdx]["remain"] = str(spboxValue)

                    if spboxValue == 0:
                        oBtn.setText("비활성화")
                        oBtn.setStyleSheet("background-color : orange; color : black;")
                        # 현재 밸브 처리(GUI-선색깔)
                        self.printLine(valveNo)
                        # GPIO 닫기 처리
                        self.rpiOut(valveNo, isOpen=False)
                        # 0초 되면, 다음걸로 넘어가기
                        self.nextValve(valveNo)
        if self.oDogFeed["isRunning"] == True:
            nDogTime = self.spDogFeedTime.value()
            nDogTime = nDogTime - 1
            if nDogTime > 0:
                self.spDogFeedTime.setValue(nDogTime)
            else:
                self.spDogFeedTime.setValue(0)

    # 다음 밸브처리
    def nextValve(self, valveNo):
        Log.d(self.TAG, "nextValve() No : {}".format(valveNo))
        """ 다음 밸브처리

        Args:
            valveNo (int): 밸브 번호
        """

        # 모터 켜기
        if valveNo == self.oIdxName["Motor"]:
            self.rpiOut(valveNo, isOpen=True)

        Log.d(self.TAG, ">> taskQueue : {}".format(self.taskQueue))

        # task 큐에 남아있다면, 
        if len(self.taskQueue) > 0:
            # 큐에서 하나를 꺼내서,
            nowTask = self.taskQueue.pop(0)
            nowValveNo = int(nowTask["valve"])
            factor = self.unitFactor[nowTask["period"][-1:]]
            # 시간(초)
            nTime = int(nowTask["period"][:-1]) * factor
            
            # 콤보박스의 번호 0 ~ 4
            idx = nowTask["no"]-1

            self.spboxList[idx]["o"].setValue(int(nTime))
            self.cbList[idx]["title"] = "Valve {}".format(nowValveNo)
            self.btnEnableList[nowTask["no"]]["o"].setText("활성화")
            self.btnEnableList[nowTask["no"]]["o"].setStyleSheet("background-color : green; color : black;")
            # 현재 밸브 처리(GUI-선색깔)
            self.printLine(nowValveNo)
            # GPIO 열기
            self.rpiOut(nowValveNo, isOpen=True)

            # Valve 4, 5 인터록 처리
            if nowValveNo >= self.oIdxName["Valve1"] and nowValveNo <= self.oIdxName["Valve3"]:
                if self.btnList[self.oIdxName["Valve4"]-1]["isOpen"] == False:
                    self.printLine(self.oIdxName["Valve4"])
                self.rpiOut(self.oIdxName["Valve4"], isOpen=True)
                self.btnEnableList[0]["o"].setText("활성화")
                self.btnEnableList[0]["o"].setStyleSheet("background-color : green; color : black;")
            elif nowValveNo == self.oIdxName["Valve5"]:
                self.printLine(self.oIdxName["Valve4"])
                self.rpiOut(self.oIdxName["Valve4"], isOpen=False)
                self.btnEnableList[0]["o"].setText("비활성화")
                self.btnEnableList[0]["o"].setStyleSheet("background-color : orange; color : black;")
        else:
            self.resetQueue()
            # 모터 토글
            self.printLine(self.oIdxName["Motor"])
            # 모터 끔
            self.rpiOut(self.oIdxName["Motor"], isOpen=False)
            self.isTaskRunning = False

    # 현재 밸브의 상태를 리턴
    def getValveStatus(self):
        """ 현재 밸브의 상태 리턴
        Return
            status(Dictonary) : d["taskQueue"], d["taskNoticeQueue"]
        """
        status = {
            "taskQueue" : self.taskQueue(),
            "taskNoticeQueue" : self.taskNoticeQueue()
        }
        return status

    # spi 통신결과 받으면,
    def onRecvResult(self, o):
        """spi 통신결과 받으면, callback

        Args:
            o (dictionary): ex> {'ch': 0, 'read': [1, 128, 0], 'outAdc': 0, 'v': 0.0, 'pressure':0.0}
        """
        # for debug
        #Log.d(self.TAG, "SPI >>> {}".format(str(o)))
        
        pressure = o["pressure"]
        txtPressure = ""
        if pressure < 0:
            txtPressure = "#0"
        else:
            txtPressure = "{} bar".format(pressure)
        
        self.pressure.setText(txtPressure)
        self.manualPressure.setText(txtPressure)

        # 압력이 1bar 이상이면, 시퀀스 시작
        if pressure >= self.startPressure:
            Log.d(self.TAG, "{} bar ↑ = {} bar".format(self.startPressure, pressure))
            if self.isTaskRunning == False and self.body.currentIndex() == self.oIdxName["MODE_AUTO"]:
                Log.d(self.TAG, "Auto mode Start...!")
                self.startTask(self.oIdxName["Motor"])
            elif self.body.currentIndex() == self.oIdxName["MODE_MANUAL"]:
                Log.d(self.TAG, "Manual mode...!")
            else:
                Log.d(self.TAG, "Alreay runnning...!")
    
    # 압력 설정값 변경될 때,
    def setPressure(self):
        strPressure = self.edPressure.text()
        prevPressure = self.startPressure
        self.startPressure = float(strPressure)
        Log.i(self.TAG, "압력 설정값 바뀜 {} ===> {}".format(prevPressure, strPressure))

    # 현재 상태값(밸브순서, 설정한 초, 압력) 저장
    def saveSetting(self):
        self.saveTime()

        seqList = []
        for i, o in enumerate(self.initQueue):
            no = o["valve"]
            if no == self.oIdxName["Valve4"]:
                no = self.oIdxName["Valve5"]
            seqList.append(no)
            self.settings.setValue("SETTING/valve"+str(o["valve"]), o["period"])

        self.settings.setValue("SETTING/Sequence", ",".join(map(str, seqList)).replace("\"", ""))
        self.settings.setValue("SETTING/feed_time", str(self.spDogFeedTime.value()) +"s")
        self.settings.setValue("SETTING/pressure", self.startPressure)

    #윈도우 닫을때
    def closeEvent(self, event):
        Log.d(self.TAG, "close window...")
        self.isTaskRunning = False
        self.timeWorker.isRunning = False
        self.timeWorker.quit()
        # 라즈베리파이 자원 해제
        self.rpiUtil.release()
        # 설정값 저장
        self.saveSetting()
        event.accept()

    @pyqtSlot(str)
    def sigTimeout(self, now):
        # 1초 마다
        self.lblTime.setText(now)
        self.checkBtnActive()

# 1초 타임아웃
class TimeWorker(QThread):
    isRunning = False
    timeout = pyqtSignal(str)

    def run(self):
        while self.isRunning:
            now = getNow()
            # 현재시간
            self.timeout.emit(now)
            # 1초 대기
            self.sleep(1)

# 현재 시간
def getNow():
    """현재 시간

    Returns:
        string: ex> '2023-09-20 09:28'
    """
    now = datetime.datetime.now()
    formattedTime = now.strftime("%Y-%m-%d %H:%M:%S")
    return formattedTime

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowTitle("Solenoid Valve Controller v0.1 [Test]")
    win.resize(625, 520)
    win.moveToCenter()
    win.show()

    sys.exit(app.exec_())

    