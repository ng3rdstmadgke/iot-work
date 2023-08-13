import pigpio
import time
from typing import Union

def int_to_binary(n: int, bits: int = 8):
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])

def bytes_to_binary(data: Union[bytearray,bytes]):
    return ','.join([int_to_binary(byte) for byte in data])

def main(debug: bool, chip_select: int, channel: int):
    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    VREF = 3.3  # A/Dコンバータの基準電圧

    # オプション (http://abyz.me.uk/rpi/pigpio/python.html#spi_open)
    # 21 20 19 18 17 16 15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
    # b  b  b  b  b  b  R  T  n  n  n  n  W  A u2 u1 u0 p2 p1 p0  m  m
    # mm: SPIモード
    # A: メインSPI(0), AuxSPI(1) どちらを利用するか選択
    # W: 3線のSPIを利用するなら(1)、4線なら(0) (メインSPIでしか利用できない)
    # あとは使いどころあるのかよくわからん、、、
    SPI_MODE = 0b00  # SPIモード0を設定。アイドル時のクロックはLOW(CPOL=0)、クロックがHIGHになるときにデータをサンプリング(CPHA=0)
    OPTION = 0b0  
    OPTION = OPTION | SPI_MODE
    CLOCK_SPEED = 50000  # 50KHz
    h = pi.spi_open(chip_select, CLOCK_SPEED, OPTION)
    try:
        while True:
            # 1bit: 0固定
            # 2bit: スタートビット (1固定)
            # 3bit: SGL/DIFF: 動作モード。疑似差動モード(0)、シングルエンドモード(1)
            # 4bit: ODD/SIGN: MCP3002で利用するチャンネル。 CH0(0), CH1(1)
            # 5bit: MSBF: 受信データの形式。MSBF + LSBF(0), MSBFのみ(1)、
            write_data = 0b0110100000000000
            write_data = write_data | (0b1 * channel) << 12  # ODD/SIGN: 入力されたチャンネルで設定
            write_data = write_data.to_bytes(2, "big")
            cnt, read_data = pi.spi_xfer(h, write_data)
            if cnt != 2:
                print("[error] skip.")
                continue
            value = int.from_bytes(read_data, "big") & 0b1111111111  # 10ビットを値として取り出す
            volt = (value / 1023.0) * VREF  # 温度センサーから入力された電圧
            temp = (volt - 0.6) / 0.01  # 電圧を温度に変換。(0℃で600mV , 1℃につき10mV増減)

            if (debug):
                print(f"w: {bytes_to_binary(write_data)}")
                print(f"r: {bytes_to_binary(read_data)}")
                print(f"value: {value}, volt: {volt}, temp: {temp}")
            else:
                print(f"Temp: {temp}")
            time.sleep(1)
    finally:
        pi.spi_close(h)
        pi.stop()
        print("[info] spi closed.")

if __name__ == "__main__":
    CHIP_SELECT = 0  # ラズパイの CE0端子, CE1端子どちらに接続するか
    CHANNEL = 0  # MCP3002のCH0端子,CH1端子どちらを利用するか
    main(True, CHIP_SELECT, CHANNEL)