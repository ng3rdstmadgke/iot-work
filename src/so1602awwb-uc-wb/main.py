# 取扱説明書:
#   https://akizukidenshi.com/download/ds/akizuki/so1602awwb-uc-wb-u_akizuki_manu.pdf
# データシート:
#   https://akizukidenshi.com/download/ds/sunlike/SO1602AWWB-UC-WB-U.pdf
from time import sleep
from typing import Union, List, Tuple
import pigpio
from pprint import pprint
from collections import OrderedDict
import enum

def write_command(pi, i2c_handler, command: int):
    control_byte = 0b00000000
    pi.i2c_write_device(i2c_handler, bytes([control_byte, command]))
    sleep(0.01)


def write_data(pi, i2c_handler, data: int):
    control_byte = 0b01000000
    pi.i2c_write_device(i2c_handler, bytes([control_byte, data]))
    sleep(0.001)


def init(pi, i2c_handler):
    sleep(0.1)
    write_command(pi, i2c_handler, 0b00000001)  # Clear Display
    sleep(0.02)
    write_command(pi, i2c_handler, 0b00000010)  # Return Home
    sleep(0.002)
    write_command(pi, i2c_handler, 0b00001111)  # Display ON
    sleep(0.002)
    write_command(pi, i2c_handler, 0b00000001)  # Clear Display
    sleep(0.02)


def main(pi, i2c_handler):
    init(pi, i2c_handler)

    text = b"hello world"
    for b in text:
        write_data(pi, i2c_handler, b)

    ddram_addr = 0b00100000  # 2行目の先頭 (0x20)
    write_command(pi, i2c_handler, 0b10000000 | ddram_addr)  # Set DDRAM RAM Address

    for i in range(0, 16):
        write_data(pi, i2c_handler, i + 0xB1)  # 0xB1 = ア
    
    write_command(pi, i2c_handler, 0b00101010)  # RE=1
    write_command(pi, i2c_handler, 0b01111001)  # SD=1
    write_command(pi, i2c_handler, 0b10000001)  # コントラストセット
    write_command(pi, i2c_handler, 0b11111111)  # 輝度 max
    write_command(pi, i2c_handler, 0b01111000)  # SD=0
    write_command(pi, i2c_handler, 0b00101000)  # 2C=高文字 28=ノーマル
    sleep(10)



if __name__ == "__main__":
    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    i2c_bus = 1
    i2c_address = 0x3C  # SA0=L (SA0=Hの場合は0x3D)  (i2cdetect 1コマンドで確認)
    i2c_flags = 0x0

    i2c_handler = pi.i2c_open(i2c_bus, i2c_address)
    try:
        main(pi, i2c_handler)
    finally:
        pi.i2c_close(i2c_handler)
        pi.stop()