# データシート
#   - https://akizukidenshi.com/download/ds/bosch/BST-BME280_DS001-10.pdf
import time
from typing import Union, List, Tuple
import pigpio
from pprint import pprint
from collections import OrderedDict
import enum


def int_to_binary(n: int, bits: int = 8) -> str:
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])

def bytes_to_binary(data: Union[bytearray,bytes]) -> List[str]:
    return [int_to_binary(byte) for byte in data]


def write_register(pi, spi_handler, register_addr: int, data: int):
    """
    レジスターに設定を書き込む
    """
    # 書込み時のregister指定は最上位ビットを0にする
    write_data = (register_addr & 0b01111111) << 8 | data
    write_data = write_data.to_bytes(2, "big")
    cnt, read_data = pi.spi_xfer(spi_handler, write_data)
    print(f"cnt={cnt}, read_data={bytes_to_binary(read_data)}")

def read_register(pi, spi_handler, register_addr: int, num_bytes: int) -> bytes:
    """
    レジスターから指定したバイト数読み取る
    """
    # 読込み時のregister指定は最上位ビットを1にする
    write_data = (register_addr | 0b10000000) << (8 * num_bytes)
    write_data = write_data.to_bytes(num_bytes + 1, "big")
    cnt, read_data = pi.spi_xfer(spi_handler, write_data)
    if cnt != (num_bytes + 1):
        raise Exception(f"ReadError: cnt={cnt} (expected={num_bytes+1})")
    return read_data[1:]

def read_calibration_data(pi, spi_handler):
    """
    キャリブレーション用のデータを取得する
    """
    cal_1 = read_register(pi, spi_handler, 0x88, 24)
    cal_2 = read_register(pi, spi_handler, 0xA1, 1)
    cal_3 = read_register(pi, spi_handler, 0xE1, 7)
    print(f"0x88 ~ 0x9F: {bytes_to_binary(cal_1)}")
    print(f"0xA1: {bytes_to_binary(cal_2)}")
    print(f"0xE1 ~ 0xE7: {bytes_to_binary(cal_3)}")

    cal_data = OrderedDict([
        # --- --- --- 0x88 ~ 0x9F --- --- ---
        ("dig_T1", int.from_bytes(cal_1[0:2]  , byteorder="little", signed=False)),
        ("dig_T2", int.from_bytes(cal_1[2:4]  , byteorder="little", signed=True)),
        ("dig_T3", int.from_bytes(cal_1[4:6]  , byteorder="little", signed=True)),
        ("dig_P1", int.from_bytes(cal_1[6:8]  , byteorder="little", signed=False)),
        ("dig_P2", int.from_bytes(cal_1[8:10] , byteorder="little", signed=True)),
        ("dig_P3", int.from_bytes(cal_1[10:12], byteorder="little", signed=True)),
        ("dig_P4", int.from_bytes(cal_1[12:14], byteorder="little", signed=True)),
        ("dig_P5", int.from_bytes(cal_1[14:16], byteorder="little", signed=True)),
        ("dig_P6", int.from_bytes(cal_1[16:18], byteorder="little", signed=True)),
        ("dig_P7", int.from_bytes(cal_1[18:20], byteorder="little", signed=True)),
        ("dig_P8", int.from_bytes(cal_1[20:22], byteorder="little", signed=True)),
        ("dig_P9", int.from_bytes(cal_1[22:24], byteorder="little", signed=True)),

        # --- --- --- 0xA1 --- --- ---
        ("dig_H1", int.from_bytes(cal_2, byteorder="little", signed=False)),

        # --- --- --- 0xE1 ~ 0xE7 --- --- ---
        ("dig_H2", int.from_bytes(cal_3[0:2], byteorder="little", signed=True)),
        ("dig_H3", int.from_bytes(cal_3[2:3], byteorder="little", signed=False)),
        ("dig_H4", cal_3[3] << 4 | (0b00001111 & cal_3[4])),
        ("dig_H5", cal_3[5] << 4 | (0b00001111 & (cal_3[4] >> 4))),
        ("dig_H6", int.from_bytes(cal_3[7:8], byteorder="little", signed=True)),
    ])
    pprint(cal_data)
    return cal_data

def read_temp(pi, spi_handler, cal_data: OrderedDict) -> Tuple[int, float]:
    """
    温度を読み取る
    """
    temp_register = 0xFA
    read_bytes = read_register(pi, spi_handler, temp_register, 3)
    # 温度は20ビットフォーマットで受信され、正値で32ビット符号付き整数
    temp_raw = int.from_bytes(read_bytes, byteorder="big") >> 4
    print(f"temp: bytes={bytes_to_binary(read_bytes)}, temp_raw={temp_raw}")

    # 以下キャリブレーション
    var1 = (((temp_raw >> 3) - (cal_data["dig_T1"] << 1)) * cal_data["dig_T2"]) >> 11
    var2 = (((((temp_raw >> 4) - cal_data["dig_T1"]) * ((temp_raw >> 4) - cal_data["dig_T1"])) >> 12) * (cal_data["dig_T3"])) >> 14
    t_fine = var1 + var2
    temp = ((t_fine * 5 + 128) >> 8) / 100
    return (t_fine, temp)

def read_pressure(pi, spi_handler, cal_data: OrderedDict, t_fine: int):
    read_bytes = read_register(pi, spi_handler, 0xF7, 3)
    # 気圧は20ビットフォーマットで受信され、正値で32ビット符号付き整数
    pressure_raw = int.from_bytes(read_bytes, byteorder="big") >> 4
    print(f"pressure: bytes={bytes_to_binary(read_bytes)}, pressure_raw={pressure_raw}")

    # 以下キャリブレーション
    var1 = t_fine - 128000
    var2 = var1 * var1 * cal_data["dig_P6"]
    var2 = var2 + ((var1 * cal_data["dig_P5"]) << 17)
    var2 = var2 + ((cal_data["dig_P4"]) << 35)
    var1 = ((var1 * var1 * cal_data["dig_P3"]) >> 8) + ((var1 * cal_data["dig_P2"]) << 12)
    var1 = ((1 << 47) + var1) * (cal_data["dig_P1"]) >> 33
    if (var1 == 0):
        return 0  # avoid exception caused by division by zero
    p = 1048576 - pressure_raw
    p = (((p << 31) - var2) * 3125) // var1
    var1 = ((cal_data["dig_P9"]) * (p >> 13) * (p >> 13)) >> 25
    var2 = ((cal_data["dig_P8"]) * p) >> 19
    p = ((p + var1 + var2) >> 8) + ((cal_data["dig_P7"]) << 4)
    return p / 256 / 100  # hPa


def read_humidity(pi, spi_handler, cal_data: OrderedDict, t_fine: int):




def main(pi, spi_handler):
    # 湿度の設定
    osrs_h = 1    # Humidity oversampling x 1
    ctrl_hum_reg  = osrs_h
    write_register(pi, spi_handler, 0xF2, ctrl_hum_reg)

    # 温度と気圧の設定
    osrs_t = 1    # Temperature oversampling x 1
    osrs_p = 1    # Pressure oversampling x 1
    mode = 3      # Normal mode
    ctrl_meas_reg = (osrs_t << 5) | (osrs_p << 2) | mode
    write_register(pi, spi_handler, 0xF4, ctrl_meas_reg)

    # その他の設定
    t_sb = 5      # Tstandby 1000ms
    filter = 0    # Filter off 
    spi3w_en = 0  # 3-wire SPI Disable
    config_reg    = (t_sb << 5) | (filter << 2) | spi3w_en
    write_register(pi, spi_handler, 0xF5, config_reg)

    # キャリブレーションデータ
    cal_data = read_calibration_data(pi, spi_handler)

    while True:
        t_fine, temp = read_temp(pi, spi_handler, cal_data)
        print(f"temp: {temp}")
        press = read_pressure(pi, spi_handler, cal_data, t_fine)
        print(f"press: {press}")
        hum = read_register(pi, spi_handler, 0xFD, 2)
        print(f"hum: {bytes_to_binary(hum)}")
        time.sleep(1)



if __name__ == "__main__":
    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    # オプション (http://abyz.me.uk/rpi/pigpio/python.html#spi_open)
    # 21 20 19 18 17 16 15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
    # b  b  b  b  b  b  R  T  n  n  n  n  W  A u2 u1 u0 p2 p1 p0  m  m
    # mm: SPIモード
    # A: メインSPI(0), AuxSPI(1) どちらを利用するか選択
    # W: 3線のSPIを利用するなら(1)、4線なら(0) (メインSPIでしか利用できない)
    # あとは使いどころあるのかよくわからん、、、
    SPI_MODE = 0b11  # SPIモード0を設定。アイドル時のクロックはHIGH(CPOL=1)、クロックがLOWになるときにデータをサンプリング(CPHA=1)
    OPTION = 0b0 | SPI_MODE
    CLOCK_SPEED = 1_000_000  # 1MHz
    SPI_CHANNEL = 0
    spi_handler = pi.spi_open(SPI_CHANNEL, CLOCK_SPEED, OPTION)

    try:
        main(pi, spi_handler)

    finally:
        pi.spi_close(spi_handler)
        pi.stop()
