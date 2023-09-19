# SolValveControl
RPi(라즈베리파이) 와 Python을 활용한 Solenoid Valve Control

### 필요한 패키지 설치
#### 1) Linux
  sudo apt-get update\
  sudo apt-get -y install python3-rpi-gpio

##### (1) SPI
    sudo raspi-config\
    9 Advanced Options > SPI > Enable
    ls /dev/*spi*

    sudo nano /etc/modules\
    마지막 줄에 spidev 추가
#### 2) Python
  pip install spidev


### 실행
sudo python ./main.py
