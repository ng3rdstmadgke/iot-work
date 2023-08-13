import pigpio
import time

def int_to_binary(n: int, bits: int = 8):
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])

def bytes_to_binary(data: bytearray):
    return ','.join([int_to_binary(byte) for byte in data])

def main(debug: bool, chip_select: int, channel: int):
    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    SERIAL_COMUNICATION_SPEED = 50000  # bit/sec
    VREF = 3.3  # ADコンバータの基準電圧
    OPTION = 0b0
    OPTION = OPTION | 3  # 
    h = pi.spi_open(chip_select, SERIAL_COMUNICATION_SPEED, OPTION)
    try:
        while True:
            # write_data = 0b0110100000000000 or 0b0111100000000000
            write_data = 0b0
            write_data = write_data | 0b1             << 14  # スタートビット (1固定)
            write_data = write_data | 0b1             << 13  # SGL/DIFF: 動作モード。疑似差動モード(0)、シングルエンドモード(1)
            write_data = write_data | (0b1 * channel) << 12  # ODD/SIGN: MCP3002で利用するチャンネル。 CH0(0), CH1(1)
            write_data = write_data | 0b1             << 11  # MSBF: 受信データの形式。MSBF + LSBF(0), MSBFのみ(1)、
            write_data = write_data.to_bytes(2, "big")
            count, read_data = pi.spi_xfer(h, write_data)
            if (debug):
                print(f"w: {bytes_to_binary(write_data)}")
                print(f"r: {bytes_to_binary(read_data)}")
            value = int.from_bytes(read_data, "big") & 0b1111111111  # 10ビットを値として取り出す
            volt = VREF * (value / 1023.0)
            temp = (volt - 0.6) / 0.01
            print(f"Value: {value}, Volt: {volt}, Temp: {temp}")
            time.sleep(1)
    finally:
        pi.spi_close(h)

if __name__ == "__main__":
    CHIP_SELECT = 0  # ラズパイの CE0, CE1どちらに接続するか
    CHANNEL = 0  # MCP3002のCH0端子,CH1端子どちらを利用するか
    main(True, CHIP_SELECT, CHANNEL)