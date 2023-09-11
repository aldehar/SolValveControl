import socket
import threading
import time

class Socket:
    ip = ""
    port = 0
    dictClient = {}

    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port

        self.init()

    def __del__(self):
        self.server_socket.close()
        print('[Socket] Server Stop...')

    def init(self):
        # 서버소켓 오픈
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.ip, self.port))

        # 클라이언트 접속 준비 완료
        self.server_socket.listen()
        print('[Socket] Server Start...')

        # 접속대기 반복(여러 클라이언트)
        while True:
            clientSocket, address = self.server_socket.accept() # 접속대기
            # 클라이언트 연결 시, 1:1 통신소켓을 오픈 +쓰레드에 전달/실행
            th = threading.Thread(target=self.recvMsg, args=(clientSocket,))  
            th.start()
            print('[Socket] connected client addr : ', address)
            self.dictClient[address] = clientSocket

            time.sleep(5)
    
    def sendMsg(self, address, msg):
        clientSocket = self.dictClient[address]
        clientSocket.sendall(msg.encode(encoding='utf-8'))

    def recvMsg(self, clientSocket):
        while True:
            data = socket.recv(100)
            msg = data.decode() 
            print('[Socket] recv msg : ', msg)
            if msg == '/end':
                break
