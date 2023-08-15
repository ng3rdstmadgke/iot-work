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
            # カソード側: LOWに設定
            pi.write(DIGIT_GPIO[digit], 0)

            # アノード側(7セグ表示): (点灯するセグメントに対応するGPIOをHIGHに設定)
            for i in range(0, 7):
                pi.write(SEG_GPIO[i], (seg_shape >> i) & 1)
            # アノード側(ドット表示): (最上位ビットが1ならドットに対応するGPIOをHIGHに設定)
            pi.write(DP_GPIO, (seg_shape >> 7) & 1)
            time.sleep(0.001)

            ############################
            # 消灯
            ############################
            # アノード側: すべてのGPIOをLOWに設定
            for i in SEG_GPIO:
                pi.write(i, 0)
            pi.write(DP_GPIO, (seg_shape >> 7) & 0)

            # カソード側: HIGHに設定
            pi.write(DIGIT_GPIO[digit], 1)


def counter(data: list[int]):
    """表示する数字をインクリメントする関数"""
    cnt = -110
    while cnt < 10000:
        time.sleep(0.1)
        cnt = round(cnt, 2) + 0.1
        ret = refresh(cnt, data)
        print(f"{cnt}: '{ret}', {[bin(i) for i in data]}")


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

    # すべてのGPIOをOUTPUTに設定
    for gpio in SEG_GPIO + DIGIT_GPIO:
        pi.set_mode(gpio, pigpio.OUTPUT)

    # GPIOの初期化
    init_gpio(pi)
    # カウンターと表示は別スレッドで動かす
    with ThreadPoolExecutor(max_workers=2) as executor:
        data = [0, 0, 0, 0]  # 各桁の点灯するセグメントがbitで格納される(displayとtaskの共有データ)
        display_future = executor.submit(display, pi, data)
        counter_future = executor.submit(counter, data)
        try:
            counter_future.result()
            display_future.result()
        finally:
            init_gpio(pi)
            pi.stop()
            print("[INFO] GPIO close.")


if __name__ == "__main__":
    main()