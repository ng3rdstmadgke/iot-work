import wiringpi as pi
import struct
import time

def get_value_from_mcp3002(ch):
    # 0b0110100000000000 or 0b0111100000000000
    senddata = 0b0
    senddata = senddata | 0b1        << 14  # スタートビット (1固定)
    senddata = senddata | 0b1        << 13  # SGL/DIFF : シングルエンドモード(1)、疑似差動モード(0)
    senddata = senddata | (0b1 * ch) << 12  # ODD/SIGN : シングルモード動作時のチャンネル CH0(0)、CH1(1)
    senddata = senddata | 0b1        << 11  # MSBF : MSB(最上位ビットから送信される)(1)もしくはLSB(最下位ビットから送信される)(0)
    buffer = senddata.to_bytes(2, 'big')
    pi.wiringPiSPIDataRW(ch , buffer)  # データの送信と同時にbufferにデータを受信する
    value = int.from_bytes(buffer, "big") & 0b1111111111  # 10ビットを値として取り出す
    return value


def main():
    SPI_CS = 0  # ラズパイの CE0, CE1どちらに接続するか (CS=Chip Select)
    SPI_CH = 0  # MCP3002のCH0端子,CH1端子どちらを利用するか
    SPI_SPEED = 1000000  # 1MHz
    VREF = 3.3  # ADコンバータの基準電圧

    pi.wiringPiSPISetup(SPI_CS, SPI_SPEED)
    while True:
        value = get_value_from_mcp3002(SPI_CH)
        volt = VREF * (value / 1023.0)
        temp = (volt - 0.6) / 0.01
        print(f"Value: {value}, Volt: {volt}, Temp: {temp}")
        time.sleep(1)

if __name__ == "__main__":
    main()