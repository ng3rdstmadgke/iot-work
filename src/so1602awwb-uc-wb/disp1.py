from time import sleep
import pigpio

def write_data(pi, i2c_handler, data: int):
    control_byte = 0b01000000  # コントロールバイト: データ書込みは bit6=1
    pi.i2c_write_device(i2c_handler, bytes([control_byte, data]))
    sleep(0.001)


def write_command(pi, i2c_handler, command: int):
    control_byte = 0b00000000  # コントロールバイト: コマンドは bit6=0
    pi.i2c_write_device(i2c_handler, bytes([control_byte, command]))
    sleep(0.05)


def init(pi, i2c_handler):
    """初期化処理"""
    # Clear Display (IS=X, RE=X, SD=0)
    #   全DDRAMに0x20を書き込み、DDRAMを0x00(1行目先頭)に設定
    #   0 0 0 0 0 0 0 1
    write_command(pi, i2c_handler, 0b00000001)

    # Return Home (IS=X, RE=0, SD=0)
    #   DDRAMを0x00(1行目先頭)に設定
    #   0 0 0 0 0 0 1 *
    write_command(pi, i2c_handler, 0b00000010)

    # Display ON/OFF Control
    #   ディスプレイ・カーソル・ブリンクのON/OFFを設定
    #   0 0 0 0 1 D C B
    #   - D: ディスプレイ (1)
    #   - C: カーソル表示 (0)
    #   - B: ブリンク表示 (0)
    write_command(pi, i2c_handler, 0b00001100)

    # Entry Mode Set (IS=0, RE=0, SD=0)
    #   データ書き込み時のカーソルの移動方向の設定
    #   0 0 0 0 0 1 I/D S
    #   - I/D: カーソルが右に移動しDDRAMアドレスがインクリメント (1)
    #   - S  : ディスプレイ全体のシフトさせない (0)
    write_command(pi, i2c_handler, 0b00000110)  # シフト設定をデフォルト値に

    # Function Set (IS=0, RE=1, SD=0)
    #   機能設定
    #   0 0 0 1 * N DH RE(0) REV
    #   - N: 2行表示 (1)
    #   - DH: 2行高表示を利用しない (0)
    #   - RE: (1)
    #   - REV: ディスプレイを反転表示しない (0)
    write_command(pi, i2c_handler, 0b00101010)  # IS=0, RE=1, SD=0

    # OLED Characterization (IS=0, RE=1, SD=0)
    #   0 1 1 1 1 0 0 SD
    #   - SD: (1)
    write_command(pi, i2c_handler, 0b01111001)  # IS=0, RE=1, SD=1

    # Set Contrast Control
    #   コントラスト設定。
    #   2バイトコマンドなので、このあとに輝度設定バイト(0x00 - 0xFF)を送信
    #   1 0 0 0 0 0 0 1
    write_command(pi, i2c_handler, 0b10000001)  # コントラストセット
    write_command(pi, i2c_handler, 0b11111111)  # 輝度 max

    # OLED Characterization (IS=0, RE=1, SD=0)
    #   0 1 1 1 1 0 0 SD
    #   - SD: (0)
    write_command(pi, i2c_handler, 0b01111000)  # IS=0, RE=1, SD=0

    # Function Set (IS=X, RE=0, SD=0)
    #   機能設定
    #   0 0 0 1 * N DH RE(0) IS
    #   - N: 2行表示 (1)
    #   - DH: 2行高表示を利用しない (0)
    #   - RE: (0)
    #   - IS: (0)
    write_command(pi, i2c_handler, 0b00101000)  # IS=0, RE=0, SD=0



def off(pi, i2c_handler):
    """終了処理"""
    write_command(pi, i2c_handler, 0b01111000)  # SD=1 (OLED Characterization)
    write_command(pi, i2c_handler, 0b00101000)  # RE=0, IS=0 (Function Set)
    write_command(pi, i2c_handler, 0b00000001)  # Clear Display
    write_command(pi, i2c_handler, 0b00000010)  # Return Home
    write_command(pi, i2c_handler, 0b00001000)  # Display, cursor, blink = OFF



def main(pi, i2c_handler):
    """
    固定表示
    """
    write_command(pi, i2c_handler, 0b00101000)  # bit2 (1: Double height, 0: Single height) (Function Set)
    # IS=0, RE=0, SD=0

    l1 = b"Temp  Pres Hum"
    for char in l1:
        write_data(pi, i2c_handler, char)

    ddram_addr = 0b00100000  # 2行目の先頭 (0x20)
    write_command(pi, i2c_handler, 0b10000000 | ddram_addr)  # Set DDRAM RAM Address
    l2 = b"24.34 1012 50.35"
    for ch in l2:
        write_data(pi, i2c_handler, ch)  # 0xB1 = ア


if __name__ == "__main__":
    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    i2c_bus = 1
    i2c_address = 0x3C  # SA0=L (SA0=Hの場合は0x3D)  (i2cdetect 1コマンドで確認)
    i2c_flags = 0x0
    i2c_handler = pi.i2c_open(i2c_bus, i2c_address)
    try:
        init(pi, i2c_handler)
        main(pi, i2c_handler)
        sleep(10)
    finally:
        off(pi, i2c_handler)
        sleep(1)
        pi.i2c_close(i2c_handler)
        pi.stop()
