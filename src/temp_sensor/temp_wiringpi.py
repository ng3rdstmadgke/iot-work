import wiringpi as pi
import time
from typing import Union

def int_to_binary(n: int, bits: int = 8):
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])

def bytes_to_binary(data: Union[bytearray,bytes]):
    return ','.join([int_to_binary(byte) for byte in data])

def main(debug: bool, chip_select: int, channel: int):
    SPI_SPEED = 1000000  # 1MHz
    VREF = 3.3  # A/Dコンバータの基準電圧

    pi.wiringPiSPISetup(chip_select, SPI_SPEED)
    while True:
        # write_data = 0b0110100000000000 or 0b0111100000000000
        write_data = 0b0
        write_data = write_data | 0b1             << 14  # スタートビット (1固定)
        write_data = write_data | 0b1             << 13  # SGL/DIFF: 動作モード。疑似差動モード(0)、シングルエンドモード(1)
        write_data = write_data | (0b1 * channel) << 12  # ODD/SIGN: MCP3002で利用するチャンネル。 CH0(0), CH1(1)
        write_data = write_data | 0b1             << 11  # MSBF: 受信データの形式。MSBF + LSBF(0), MSBFのみ(1)、
        buffer = write_data.to_bytes(2, 'big')
        pi.wiringPiSPIDataRW(chip_select , buffer)  # データの送信と同時にbufferにデータを受信する
        value = int.from_bytes(buffer, "big") & 0b1111111111  # 10ビットを値として取り出す
        volt = VREF * (value / 1023.0)
        temp = (volt - 0.6) / 0.01
        if (debug):
            print(f"w: {bytes_to_binary(write_data.to_bytes(2, 'big'))}")
            print(f"r: {bytes_to_binary(buffer)}")
            print(f"value: {value}, volt: {volt}, Temp: {temp}")
        else:
            print(f"Temp: {temp}")
        time.sleep(1)

if __name__ == "__main__":
    CHIP_SELECT = 0  # ラズパイの CE0, CE1どちらに接続するか
    CHANNEL = 0  # MCP3002のCH0端子,CH1端子どちらを利用するか
    main(True, CHIP_SELECT, CHANNEL)