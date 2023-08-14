from concurrent.futures import ThreadPoolExecutor
import time
import pigpio

SEG_SHAPE = [
    # g -> aの順
    0b0111111, 
    0b0000110,
    0b1011011,
    0b1001111,
    0b1100110,
    0b1101101,
    0b1111101,
    0b0000111,
    0b1111111,
    0b1101111,
    0b0000000,
]

# 7セグ表示に利用するGPIO (a -> gの順)
SEG_GPIO = [21, 22, 23, 24, 25, 26, 27]
# 表示する桁を制御するGPIO (4桁目 -> 1桁目 の順)
DIGIT_GPIO = [20, 19, 18, 17]

def init_gpio(pi):
    """gpioをリセットす関数"""
    for gpio in DIGIT_GPIO:
        pi.write(gpio, 1)
    for gpio in SEG_GPIO:
        pi.write(gpio, 0)


def display(pi, data: list[int]):
    """ダイナミック制御で4桁の7セグを表示する関数"""
    while True:
        for digit, n in enumerate(data):
            pi.write(DIGIT_GPIO[digit], 0)
            for i in range(0, 7):
                pi.write(SEG_GPIO[i], (SEG_SHAPE[n] >> i) & 1)
            time.sleep(0.0001)

            # リセット
            for i in SEG_GPIO:
                pi.write(i, 0)

            # 消灯
            pi.write(DIGIT_GPIO[digit], 1)


def refresh(n: int, data: list[int]):
    """表示する数字を更新する関数"""
    new_data = [int(i) for i in str(n).zfill(4)]
    for i in range(0, 4):
       data[i] = new_data[i]


def counter(data: list[int]):
    """表示する数字をインクリメントする関数"""
    cnt = 0
    while cnt < 1000:
        time.sleep(0.1)
        cnt = cnt + 1
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
    try:
        data = [0, 0, 0, 0]
        # カウンターと表示は別スレッドで動かす
        with ThreadPoolExecutor(max_workers=2) as executor:
            display_result = executor.submit(display, pi, data)
            counter_result = executor.submit(counter, data)
            display_result.result()
            counter_result.result()
    finally:
        init_gpio(pi)
        pi.stop()
        print("[info] closed.")


if __name__ == "__main__":
    main() 