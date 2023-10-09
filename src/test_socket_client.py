import sys
import socket
import threading
import time
import typing

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel,QSpinBox, QComboBox, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QMessageBox, QLineEdit, QPlainTextEdit
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QThread

class ClientWin(QWidget):
    isConnected = False
    client_socket = None

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        vLayout = QVBoxLayout()

        hTopLayout = QHBoxLayout()
        lblIp = QLabel("IP")
        self.edIp = QLineEdit()
        self.edIp.setPlaceholderText("IP")
        hTopLayout.addWidget(lblIp)
        hTopLayout.addWidget(self.edIp)
        lblPort = QLabel("Port")
        self.edPort = QLineEdit()
        self.edPort.setPlaceholderText("Port")
        self.btnConnect = QPushButton("Connect")
        self.btnConnect.clicked.connect(self.onBtnClicked)

        hTopLayout.addWidget(lblPort)
        hTopLayout.addWidget(self.edPort)
        hTopLayout.addWidget(self.btnConnect)
        
        vLayout.addLayout(hTopLayout)

        lblTx = QLabel("Tx")
        vLayout.addWidget(lblTx)

        self.edTx = QPlainTextEdit()
        vLayout.addWidget(self.edTx)

        lblRx = QLabel("Rx")
        vLayout.addWidget(lblRx)
        
        self.edRx = QPlainTextEdit()
        vLayout.addWidget(self.edRx)

        lblSystemMsg = QLabel("System Message")
        vLayout.addWidget(lblSystemMsg)
        
        self.edSystemMsg = QPlainTextEdit()
        self.edSystemMsg.setReadOnly(True)
        vLayout.addWidget(self.edSystemMsg)

        hBottomLayout = QHBoxLayout()
        self.edSend = QLineEdit()
        self.edSend.setPlaceholderText("Send")
        self.btnSend = QPushButton("Send")
        self.btnSend.clicked.connect(self.onBtnClicked)

        hBottomLayout.addWidget(self.edSend)
        hBottomLayout.addWidget(self.btnSend)

        vLayout.addLayout(hBottomLayout)
        self.setLayout(vLayout)

    def onBtnClicked(self):
        sender = self.sender()

        if sender == self.btnConnect:
            addr = self.edIp.text()
            port = self.edPort.text()
            
            self.connect(addr, port)

        elif sender == self.btnSend:
            msg = self.edSend.text()
            self.sendMsg(msg)
    
    def connect(self, addr, port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((addr, int(port)))

            self.isConnected = True
            th = threading.Thread(target=self.recvMsg, args=(self.client_socket,))  
            th.start()

            print(">>> [{}] - [{}]".format(addr, port))
            self.edSystemMsg.appendPlainText("[정보] {}:{} 서버와 연결되었습니다.".format(addr, port))
            
        except ConnectionRefusedError as e:
            self.edSystemMsg.appendPlainText("[에러] {}".format(str(e)))

    def recvMsg(self, client_socket):
        while self.isConnected:
            data = client_socket.recv(1024)
            data = str(data, encoding="utf-8")
            self.edRx.appendPlainText("{}".format(data))

    def sendMsg(self, msg):
        if self.isConnected:
            self.client_socket.send(msg.encode())
            self.edTx.appendPlainText("{}".format(msg))

    def closeEvent(self, event):
        print("[정보] 클라이언트 창 닫는중...")
        self.sendMsg("/end")
        self.isConnected = False
        if self.client_socket != None:
            self.client_socket.close()
        event.accept()

class SocketClient(QThread):
    sendMsg = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def sendMsg(self):
        self.sendMsg.emit("")

def execute():
    app = QApplication(sys.argv)
    win = ClientWin()

    win.edIp.setText("127.0.0.1")
    win.edPort.setText("3333")

    win.setWindowTitle("Socket Client v0.01")
    win.setGeometry(300, 300, 625, 575)
    win.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    execute()