import time
from typing import Union
import pigpio

def int_to_binary(n: int, bits: int = 8):
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])

def bytes_to_binary(data: Union[bytearray,bytes]):
    return ','.join([int_to_binary(byte) for byte in data])


def write_register(pi, spi_handler, register_addr: int, data: int):
    # 書込み時のregister指定は最上位ビットを0にする
    write_data = (register_addr & 0b01111111) << 8 | data
    write_data = write_data.to_bytes(2, "big")
    pi.spi_xfer(spi_handler, write_data)

def read_register(pi, spi_handler, register_addr: int, num_bytes: int) -> int:
    # 読込み時のregister指定は最上位ビットを1にする
    write_data = (register_addr | 0b10000000) << (8 * num_bytes)
    write_data = write_data.to_bytes(num_bytes + 1, "big")
    cnt, read_data = pi.spi_xfer(spi_handler, write_data)
    print(f"cnt: {cnt}, read_data: {bytes_to_binary(read_data)}")
    value = int.from_bytes(read_data[1:1 + num_bytes], "big")
    return value


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
    while True:
        result = read_register(pi, spi_handler, 0xFA, 3)
        print(f"temp: {int_to_binary(result)}")
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
