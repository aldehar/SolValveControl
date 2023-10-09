import sys
import threading
import time
import socket

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel,QSpinBox, QComboBox, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QMessageBox, QLineEdit, QPlainTextEdit
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot

class ServerWin(QWidget):
    isRunning = False
    clientList = []

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
        self.btnStart = QPushButton("Start")
        self.btnStart.clicked.connect(self.onBtnClicked)

        hTopLayout.addWidget(lblPort)
        hTopLayout.addWidget(self.edPort)
        hTopLayout.addWidget(self.btnStart)
        
        vLayout.addLayout(hTopLayout)

        lblTx = QLabel("Tx")
        vLayout.addWidget(lblTx)

        self.edTx = QPlainTextEdit()
        self.edTx.setReadOnly(True)
        vLayout.addWidget(self.edTx)

        lblRx = QLabel("Rx")
        vLayout.addWidget(lblRx)
        
        self.edRx = QPlainTextEdit()
        self.edRx.setReadOnly(True)
        vLayout.addWidget(self.edRx)

        lblSystemMsg = QLabel("System Message")
        vLayout.addWidget(lblSystemMsg)
        
        self.edSystemMsg = QPlainTextEdit()
        self.edSystemMsg.setReadOnly(True)
        vLayout.addWidget(self.edSystemMsg)

        hBottomLayout = QHBoxLayout()
        self.edSendIp = QLineEdit()
        self.edSendIp.setPlaceholderText("Send IP")
        self.edSend = QLineEdit()
        self.edSend.setPlaceholderText("Send")
        self.btnSend = QPushButton("Send")
        self.btnSend.clicked.connect(self.onBtnClicked)

        hBottomLayout.addWidget(self.edSendIp)
        hBottomLayout.addWidget(self.edSend)
        hBottomLayout.addWidget(self.btnSend)

        vLayout.addLayout(hBottomLayout)
        self.setLayout(vLayout)

    def onBtnClicked(self):
        sender = self.sender()

        if sender == self.btnStart:
            addr = self.edIp.text()
            port = self.edPort.text()

            if len(addr) > 0 and len(port) > 0:
                self.initSocket(addr, port)
            else:
                self.edSystemMsg.appendPlainText("[경고] IP 주소 혹은 Port 가 비어있습니다.")

        elif sender == self.btnSend:
            addr = self.edSendIp.text()
            msg = self.edSend.text()
            self.sendMsg(addr, msg)
    
    def initSocket(self, address, port):
        try:
            # 서버소켓 오픈
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((address, int(port)))
        except Exception as e:
            pass
        else:
            self.isRunning = True
            th = threading.Thread(target=self.listen, args=(self.server_socket,))  
            th.start()
            
    def listen(self, server_socket):
        # 클라이언트 접속 준비 완료
        self.server_socket.listen()

        self.edSystemMsg.appendPlainText("[정보] 서버가 시작되었습니다.")
        
        # 접속대기 반복(여러 클라이언트)
        while self.isRunning:
            clientSocket, addr = self.server_socket.accept()

            print(">>> [{}]".format(addr))
            self.edSystemMsg.appendPlainText('[정보] 연결된 클라이언트 주소 : {}_{}'.format(addr[0], addr[1]))
            self.edSendIp.setText(addr[0])
            self.clientList.append(clientSocket)

            th = threading.Thread(target=self.recvMsg, args=((addr[0],addr[1]), clientSocket,))  
            th.start()
            
            time.sleep(1)

    def recvMsg(self, addr, clientSocket):
        while self.isRunning:
            try:
                data = clientSocket.recv(1024)
                msg = data.decode() 
                
                self.edRx.appendPlainText("[{}] - {}".format(addr, msg))
                
                if msg == '/end':
                    self.removeClient(addr)
                    break
            
            except Exception as e:
                self.removeClient(addr)

    def removeClient(self, addr):
        self.edSystemMsg.appendPlainText("[{}] 의 연결이 끊어졌습니다.".format(addr))
        try:
            clientSocket = self.clientList[0]
            if len(self.clientList) > 0:
                self.clientList.remove(clientSocket)
            clientSocket.close()
        except Exception as e:
            pass
            #print("removeClient() error occured : ", e)

    def sendMsg(self, addr, msg):
        print("sendMsg [{}] >>>>> [{}]".format(addr, msg))
        if self.isRunning:
            clientSocket = self.clientList[0]
            clientSocket.send(msg.encode(encoding='utf-8'))
        
            self.edTx.appendPlainText("[{}] - {}".format(addr, msg))
        else:
            self.edSystemMsg.appendPlainText("[경고] 서버가 시작 되지 않았습니다.")

    def closeEvent(self, event):
        print("[정보] close window...")
        self.isRunning = False
        self.server_socket.close()
        event.accept()

def execute():
    app = QApplication(sys.argv)
    win = ServerWin()

    win.edIp.setText("127.0.0.1")
    win.edPort.setText("3333")

    win.setWindowTitle("Socket Server v0.01")
    win.setGeometry(300, 300, 625, 575)
    win.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    execute()