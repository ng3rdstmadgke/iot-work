import time
from typing import Union, List, Tuple
import pigpio
from pprint import pprint
from collections import OrderedDict


####################################
# ユーティリティ
####################################
def int_to_binary(n: int, bits: int = 8) -> str:
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])


def bytes_to_binary(data: Union[bytearray,bytes]) -> List[str]:
    return [int_to_binary(byte) for byte in data]


####################################
# センサー関連
####################################
def write_register(pi, spi_handler, register_addr: int, data: int):
    """
    レジスターに設定を書き込む
    """
    # 書込み時のregister指定は最上位ビットを0にする
    write_data = (register_addr & 0b01111111) << 8 | data
    write_data = write_data.to_bytes(2, "big")
    cnt, read_data = pi.spi_xfer(spi_handler, write_data)
    #print(f"cnt={cnt}, read_data={bytes_to_binary(read_data)}")


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
    データシートの「4.2.2 Trimming parameter readout」を参照
    """
    cal_1 = read_register(pi, spi_handler, 0x88, 24)
    cal_2 = read_register(pi, spi_handler, 0xA1, 1)
    cal_3 = read_register(pi, spi_handler, 0xE1, 7)
    #print(f"0x88 ~ 0x9F: {bytes_to_binary(cal_1)}")
    #print(f"0xA1: {bytes_to_binary(cal_2)}")
    #print(f"0xE1 ~ 0xE7: {bytes_to_binary(cal_3)}")

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
    #pprint(cal_data)
    return cal_data


def read_temp(pi, spi_handler, cal_data: OrderedDict) -> Tuple[int, float]:
    """
    温度を読み取る
    """
    temp_register = 0xFA
    read_bytes = read_register(pi, spi_handler, temp_register, 3)
    # 温度は20ビットフォーマットで受信され、正値で32ビット符号付き整数
    temp_raw = int.from_bytes(read_bytes, byteorder="big") >> 4
    #print(f"temp: bytes={bytes_to_binary(read_bytes)}, temp_raw={temp_raw}")

    # 以下キャリブレーション (データシートの「4.2.3 Compensation formulas」を参照)
    var1 = (((temp_raw >> 3) - (cal_data["dig_T1"] << 1)) * cal_data["dig_T2"]) >> 11
    var2 = (((((temp_raw >> 4) - cal_data["dig_T1"]) * ((temp_raw >> 4) - cal_data["dig_T1"])) >> 12) * (cal_data["dig_T3"])) >> 14
    t_fine = var1 + var2
    temp = ((t_fine * 5 + 128) >> 8) / 100  # DegC
    return (t_fine, temp)


def read_pressure(pi, spi_handler, cal_data: OrderedDict, t_fine: int) -> float:
    read_bytes = read_register(pi, spi_handler, 0xF7, 3)
    # 気圧は20ビットフォーマットで受信され、正値で32ビット符号付き整数
    pressure_raw = int.from_bytes(read_bytes, byteorder="big") >> 4
    #print(f"pressure: bytes={bytes_to_binary(read_bytes)}, pressure_raw={pressure_raw}")

    # 以下キャリブレーション (データシートの「4.2.3 Compensation formulas」を参照)
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


def read_humidity(pi, spi_handler, cal_data: OrderedDict, t_fine: int) -> float:
    read_bytes = read_register(pi, spi_handler, 0xFD, 2)
    # 湿度は16ビットフォーマットで受信され、32ビット符号付き整数で保存
    humidity_raw = int.from_bytes(read_bytes, byteorder="big")
    #print(f"pressure: bytes={bytes_to_binary(read_bytes)}, humidity_raw={humidity_raw}")

    # 以下キャリブレーション (データシートの「4.2.3 Compensation formulas」を参照)
    v_x1_u32r = t_fine - 76800
    v_x1_u32r = (
        (
            (((humidity_raw << 14) - ((cal_data["dig_H4"]) << 20) - ((cal_data["dig_H5"]) * v_x1_u32r)) + (16384)) >> 15
        ) * (
            ((((((v_x1_u32r * (cal_data["dig_H6"])) >> 10) * (((v_x1_u32r * (cal_data["dig_H3"])) >> 11) + 32768)) >> 10) + 2097152) * (cal_data["dig_H2"]) + 8192) >> 14
        )
    )
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * (cal_data["dig_H1"])) >> 4))
    v_x1_u32r = 0 if (v_x1_u32r < 0) else v_x1_u32r
    v_x1_u32r = 419430400 if (v_x1_u32r > 419430400) else v_x1_u32r
    return (v_x1_u32r >> 12) / 1024  # %RH


####################################
# ディスプレイ関連
####################################
def write_display_data(pi, i2c_handler, data: int):
    control_byte = 0b01000000  # コントロールバイト: データ書込みは bit6=1
    pi.i2c_write_device(i2c_handler, bytes([control_byte, data]))
    time.sleep(0.001)


def write_display_command(pi, i2c_handler, command: int):
    control_byte = 0b00000000  # コントロールバイト: コマンドは bit6=0
    pi.i2c_write_device(i2c_handler, bytes([control_byte, command]))
    time.sleep(0.05)

def display_init(pi, i2c_handler):
    """初期化処理"""
    write_display_command(pi, i2c_handler, 0b00000001)
    write_display_command(pi, i2c_handler, 0b00000010)
    write_display_command(pi, i2c_handler, 0b00001100)
    write_display_command(pi, i2c_handler, 0b00000110)  # シフト設定をデフォルト値に
    write_display_command(pi, i2c_handler, 0b00101010)  # IS=0, RE=1, SD=0
    write_display_command(pi, i2c_handler, 0b01111001)  # IS=0, RE=1, SD=1
    write_display_command(pi, i2c_handler, 0b10000001)  # コントラストセット
    write_display_command(pi, i2c_handler, 0b11111111)  # 輝度 max
    write_display_command(pi, i2c_handler, 0b01111000)  # IS=0, RE=1, SD=0
    write_display_command(pi, i2c_handler, 0b00101000)  # IS=0, RE=0, SD=0

def display_off(pi, i2c_handler):
    """終了処理"""
    write_display_command(pi, i2c_handler, 0b01111000)  # SD=1 (OLED Characterization)
    write_display_command(pi, i2c_handler, 0b00101000)  # RE=0, IS=0 (Function Set)
    write_display_command(pi, i2c_handler, 0b00000001)  # Clear Display
    write_display_command(pi, i2c_handler, 0b00000010)  # Return Home
    write_display_command(pi, i2c_handler, 0b00001000)  # Display, cursor, blink = OFF

def display(pi, i2c_handler, t: float, p: float, h: float):
    l1 = b"Temp Press  Hum"
    for char in l1:
        write_display_data(pi, i2c_handler, char)

    ddram_addr = 0b00100000  # 2行目の先頭 (0x20)
    write_display_command(pi, i2c_handler, 0b10000000 | ddram_addr)  # Set DDRAM RAM Address
    dt = str(round(t,1)).ljust(4)
    dp = str(round(p,1)).ljust(6)
    dh = str(round(h, 1)).ljust(4)
    l2 = f"{dt} {dp} {dh}".ljust(20).encode('utf-8')
    #print(l2)
    for ch in l2:
        write_display_data(pi, i2c_handler, ch)  # 0xB1 = ア


####################################
# メイン
####################################
def main(pi, spi_handler, i2c_handler):
    # 動作設定
    config_reg = 0x5F
    t_sb = 0b000    # 測定待機時間 0.5ms
    filter = 0b101  # IIRフィルター係数 16
    spi3w_en = 0b0  # 4線式SPI
    reg_data    = (t_sb << 5) | (filter << 2) | spi3w_en
    write_register(pi, spi_handler, config_reg, reg_data)

    # 温度・気圧測定の設定
    ctrl_meas_reg = 0xF4
    osrs_t = 0b010  # 温度 オーバーサンプリングx2
    osrs_p = 0b101  # 気圧 オーバーサンプリングx16
    mode = 0b11     # ノーマルモード
    reg_data = (osrs_t << 5) | (osrs_p << 2) | mode
    write_register(pi, spi_handler, ctrl_meas_reg, reg_data)

    # 湿度測定の設定
    ctrl_hum_reg = 0xF2
    osrs_h = 0b001  # 湿度 オーバーサンプリングx1
    reg_data  = osrs_h
    write_register(pi, spi_handler, ctrl_hum_reg, reg_data)

    # キャリブレーションデータ
    cal_data = read_calibration_data(pi, spi_handler)

    while True:
        t_fine, temp = read_temp(pi, spi_handler, cal_data)
        print(f"温度: {temp} DegC")
        press = read_pressure(pi, spi_handler, cal_data, t_fine)
        print(f"気圧: {press} hPa")
        hum = read_humidity(pi, spi_handler, cal_data, t_fine)
        print(f"湿度: {hum} %RH")
        print()
        display(pi, i2c_handler, temp, press, hum)
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
    spi_mode = 0b11  # SPIモード11を設定。アイドル時のクロックはHIGH(CPOL=1)、クロックがLOWになるときにデータをサンプリング(CPHA=1)
    spi_option = 0b0 | spi_mode
    spi_clock_speed = 1_000_000  # 1MHz
    spi_channel = 0
    spi_handler = pi.spi_open(spi_channel, spi_clock_speed, spi_option)

    i2c_bus = 1
    i2c_address = 0x3C  # SA0=L (SA0=Hの場合は0x3D)  (i2cdetect 1コマンドで確認)
    i2c_flags = 0x0
    i2c_handler = pi.i2c_open(i2c_bus, i2c_address)

    try:
        display_init(pi, i2c_handler)
        main(pi, spi_handler, i2c_handler)
    finally:
        display_off(pi, i2c_handler)
        pi.i2c_close(i2c_handler)
        pi.spi_close(spi_handler)
        pi.stop()