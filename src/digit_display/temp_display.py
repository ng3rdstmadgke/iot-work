from concurrent.futures import ThreadPoolExecutor
import time
import pigpio

SEG_SHAPE = {
    # g -> aの順
    "0":  0b0111111,
    "1":  0b0000110,
    "2":  0b1011011,
    "3":  0b1001111,
    "4":  0b1100110,
    "5":  0b1101101,
    "6":  0b1111101,
    "7":  0b0000111,
    "8":  0b1111111,
    "9":  0b1101111,
    "-":  0b1000000,
    "E":  0b1111001,
    "A":  0b1110111,
    "C":  0b0111001,
    " ":  0b0000000,
    "":   0b0000000,
}

# 7セグ表示に利用するGPIO (a -> gの順)
SEG_GPIO = [21, 22, 23, 24, 25, 26, 27]
# 表示する桁を制御するGPIO (4桁目 -> 1桁目 の順)
DIGIT_GPIO = [20, 19, 18, 17]
DP_GPIO = 6

def init_gpio(pi):
    """gpioをリセットす関数"""
    for gpio in SEG_GPIO:
        pi.write(gpio, 0)
    for gpio in DIGIT_GPIO:
        pi.write(gpio, 1)


def display(pi, data: list[int]):
    """ダイナミック制御で4桁の7セグを表示する関数"""
    while True:

        for digit, seg_shape in enumerate(data):
            #print([bin(i) for i in data])
            pi.write(DIGIT_GPIO[digit], 0)
            for i in range(0, 7):
                pi.write(SEG_GPIO[i], (seg_shape >> i) & 1)
            pi.write(DP_GPIO, (seg_shape >> 7) & 1)
            time.sleep(0.001)

            # リセット
            for i in SEG_GPIO:
                pi.write(i, 0)
            pi.write(DP_GPIO, (seg_shape >> 7) & 0)

            # 消灯
            pi.write(DIGIT_GPIO[digit], 1)

def refresh(f: float, data: list[int]):
    fr = round(f, 1)
    if fr >= 1000 or fr <= -100:
        fs = "EEEE"
    else:
        fs = str(round(f, 1))
        fs = f"{fs: >5}" if "." in fs else f"{fs: >4}"
        #print(f"fs: '{fs}'")
    data_idx = 0
    for e in fs:
        if e == ".":
            # .の場合は直前の要素にドットフラグを設定する
            data[data_idx - 1] = data[data_idx - 1] | 1 << 7
            #print(f"e: {e}, data[{data_idx} - 1]: {bin(data[data_idx - 1])}")
        else:
            data[data_idx] = SEG_SHAPE[e]
            #print(f"e: {e}, data[{data_idx}]: {bin(data[data_idx])}")
            data_idx = data_idx + 1


def temp_sensor(pi, spi_handler, data: list[int]):
    VREF = 3.3  # A/Dコンバータの基準電圧
    CHANNEL = 0  # MCP3002のCH0端子,CH1端子どちらを利用するか
    while True:
        # 1bit: 0固定
        # 2bit: スタートビット (1固定)
        # 3bit: SGL/DIFF: 動作モード。疑似差動モード(0)、シングルエンドモード(1)
        # 4bit: ODD/SIGN: MCP3002で利用するチャンネル。 CH0(0), CH1(1)
        # 5bit: MSBF: 受信データの形式。MSBF + LSBF(0), MSBFのみ(1)、
        write_data = 0b0110100000000000
        write_data = write_data | (0b1 * CHANNEL) << 12  # ODD/SIGN: 入力されたチャンネルで設定
        write_data = write_data.to_bytes(2, "big")
        cnt, read_data = pi.spi_xfer(spi_handler, write_data)
        if cnt != 2:
            print("[error] skip.")
            continue
        value = int.from_bytes(read_data, "big") & 0b1111111111  # 10ビットを値として取り出す
        volt = (value / 1023.0) * VREF  # 温度センサーから入力された電圧
        temp = (volt - 0.6) / 0.01  # 電圧を温度に変換。(0℃で600mV , 1℃につき10mV増減)
        refresh(temp, data)
        print(f"value: {value}, volt: {volt}, temp: {temp}")
        time.sleep(3)

def main():

    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    # SPIオープン
    CHIP_SELECT = 0  # ラズパイの CE0端子, CE1端子どちらに接続するか
    SPI_MODE = 0b00  # SPIモード0を設定。アイドル時のクロックはLOW(CPOL=0)、クロックがHIGHになるときにデータをサンプリング(CPHA=0)
    OPTION = 0b0 | SPI_MODE
    CLOCK_SPEED = 50000  # 50KHz
    spi_handler = pi.spi_open(CHIP_SELECT, CLOCK_SPEED, OPTION)

    # すべてのGPIOをOUTPUTに設定
    for gpio in SEG_GPIO + DIGIT_GPIO:
        pi.set_mode(gpio, pigpio.OUTPUT)

    # GPIOの初期化
    init_gpio(pi)
    data = [0, 0, 0, 0]
    # カウンターと表示は別スレッドで動かす
    with ThreadPoolExecutor(max_workers=2) as executor:
        display_future = executor.submit(display, pi, data)
        counter_future = executor.submit(temp_sensor, pi, spi_handler, data)
        try:
            counter_future.result()
            display_future.result()
        finally:
            pi.spi_close(spi_handler)
            init_gpio(pi)
            pi.stop()
            print("[INFO] GPIO close.")


if __name__ == "__main__":
    main()
