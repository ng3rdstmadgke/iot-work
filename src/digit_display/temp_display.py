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

# 7セグ表示を制御するGPIO (a -> gの順)
SEG_GPIO = [21, 22, 23, 24, 25, 26, 27]
# "." 表示を制御するGPIO
DP_GPIO = 6
# 表示する桁を制御するGPIO (4桁目 -> 1桁目 の順)
DIGIT_GPIO = [20, 19, 18, 17]

def display(pi, data: list[int]):
    """ダイナミック制御で4桁の7セグを表示する関数"""
    while True:
        for digit, seg_shape in enumerate(data):
            ############################
            # 点灯
            ############################
            # カソード側: LOW
            pi.write(DIGIT_GPIO[digit], 0)

            # アノード側(7セグ表示): (点灯するセグメントに対応するGPIOをHIGHにする)
            for i in range(0, 7):
                pi.write(SEG_GPIO[i], (seg_shape >> i) & 1)

            # アノード側(ドット表示): (最上位ビットが1ならドットに対応するGPIOをHIGHにする)
            pi.write(DP_GPIO, (seg_shape >> 7) & 1)

            time.sleep(0.001)

            ############################
            # 消灯
            ############################
            # アノード側: すべてのGPIOをLOWにする
            for i in SEG_GPIO:
                pi.write(i, 0)
            pi.write(DP_GPIO, (seg_shape >> 7) & 0)

            # カソード側: HIGH
            pi.write(DIGIT_GPIO[digit], 1)

def task(pi, spi_handler, data: list[int]):
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

def refresh(f: float, data: list[int]):
    # -999 ~ 9999
    data_len = len(data)
    ip, fp = str(round(float(f), 3)).split(".")
    fp = fp[:data_len - len(ip)].ljust(data_len - len(ip), "0")
    idx = 0
    for e in ip:
        data[idx] = SEG_SHAPE[e]
        idx = idx + 1
    if idx == 4:
        return ip
    data[idx - 1] = data[idx - 1] | 1 << 7 # 小数点を付与
    for e in fp:
        data[idx] = SEG_SHAPE[e]
        idx = idx + 1
    return f"{ip}.{fp}"

def init_gpio(pi):
    """gpioをリセットす関数"""
    for gpio in SEG_GPIO:
        pi.write(gpio, 0)
    for gpio in DIGIT_GPIO:
        pi.write(gpio, 1)

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
    # 温度測定とディスプレイ表示は別スレッドで動かす
    with ThreadPoolExecutor(max_workers=2) as executor:
        data = [0, 0, 0, 0]  # 各桁の点灯するセグメントがbitで格納される(displayとtaskの共有データ)
        display_future = executor.submit(display, pi, data)
        counter_future = executor.submit(task, pi, spi_handler, data)
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
