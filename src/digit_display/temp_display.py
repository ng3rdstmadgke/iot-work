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


def counter(data: list[int]):
    """表示する数字をインクリメントする関数"""
    cnt = -99.0
    while cnt < 1000:
        time.sleep(0.1)
        cnt = cnt + 0.1
        refresh(cnt, data)

def main():

    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    # すべてのGPIOをOUTPUTに設定
    for gpio in SEG_GPIO + DIGIT_GPIO:
        pi.set_mode(gpio, pigpio.OUTPUT)

    # GPIOの初期化
    init_gpio(pi)
    data = [0, 0, 0, 0]
    # カウンターと表示は別スレッドで動かす
    with ThreadPoolExecutor(max_workers=2) as executor:
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
