import wiringpi as pi
import struct
import time

def get_value(ch):
    """
    MCP3002
    ■ データシート: https://akizukidenshi.com/download/ds/microchip/mcp3002.pdf

    ■ 送信データ
    送信データは16ビット

    1. (固定で0)
    2. スタートビット (固定で1)
    3. SGL/DIFF : シングルエンドモード(1)または擬似差動モード(0)を選択
    4. ODD/SIGN : シングルエンドモードで使用されるチャンネルを選択。CH0(0)もしくはCH1(1)
    5. MSBF : 受信データのフォーマットを選択。MSB(最上位ビットから送信される)(1)もしくはLSB(最下位ビットから送信される)(0)
    以降すべて0


    ■ ピン
    Vdd CLK DOUT DIN

    CS  CH0 CH1  GND

    - Vdd: 電源 (3.3v)
    - CLK: SCKL(シリアルクロック)端子に接続(通信するデバイス同士のタイミング合わせで利用)
    - DOUT: MOSI(Master Out Slave In)端子に接続 (接続機器からラズパイへのデータ入力)
    - DIN: MISO(Master In Slave Out)端子に接続 (ラズパイから接続機器へのデータ入力)
    - CS: CE0(CE1)端子に接続 (ラズパイからデバイスを制御。通信時にCEをLOWにする)
    - CH0: アナログデバイスの出力端子に接続
    - CH1: アナログデバイスの出力端子に接続
    - GND: GND端子に接続
    """
    #senddata = 0b0110100000000000 | (0b0001000000000000 * ch) 
    senddata = 0b0
    senddata = senddata | 0b1        << 14  # スタートビット (1固定)
    senddata = senddata | 0b1        << 13  # SGL/DIFF : シングルエンドモード(1)、疑似差動モード(0)
    senddata = senddata | (0b1 * ch) << 12  # ODD/SIGN : シングルモード動作時のチャンネル CH0(0)、CH1(1)
    senddata = senddata | 0b1        << 11  # MSBF : MSB(最上位ビットから送信される)(1)もしくはLSB(最下位ビットから送信される)(0)
    buffer = senddata.to_bytes(2, 'big')
    pi.wiringPiSPIDataRW(ch , buffer)  # データの送信と同時にbufferにデータを受信する
    value = int.from_bytes(buffer, "big") & 0b1111111111  # 10ビットを値として取り出す
    return value


SPI_CS = 0  # ラズパイの CE0, CE1どちらにつなげるか (Chip Select, Chip Enable, Slave Select) 
SPI_CH = 0  # CH0,CH1どちらのチャンネルを読み込むか
SPI_SPEED = 1000000  # 1MHz
VREF = 3.3  # ADコンバータへの入力電圧

pi.wiringPiSPISetup(SPI_CS, SPI_SPEED)

while True:
    value = get_value(SPI_CH)
    volt = VREF * (value / 1023.0)
    # MCP9700E
    #   データシート: https://akizukidenshi.com/download/mcp9700.pdf
    #   mcp9700Eは0℃の時に500mVで1℃につき10mV増減する仕様
    #temp = (volt - 0.5) / 0.01

    # LM61CIZ
    #   データシート: https://www.ti.com/cn/lit/ds/symlink/lm61.pdf
    #   - -30℃~100℃ に対応する 300mV~1600mV の電圧を出力します。
    #   - 0℃の時は600mV
    #   - 1℃につき 10mV 増減する
    temp = (volt - 0.6) / 0.01
    print(f"Value: {value}, Volt: {volt}, Temp: {temp}")
    time.sleep(1)