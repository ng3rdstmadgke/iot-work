# 取扱説明書:
#   https://akizukidenshi.com/download/ds/akizuki/so1602awwb-uc-wb-u_akizuki_manu.pdf
# データシート:
#   https://akizukidenshi.com/download/ds/sunlike/SO1602AWWB-UC-WB-U.pdf
#
# LCDの使い方(AE-AQM1602A)基礎編:
#   https://nobita-rx7.hatenablog.com/entry/27983030
from time import sleep
import pigpio

def write_data(pi, i2c_handler, data: int):
    control_byte = 0b01000000
    pi.i2c_write_device(i2c_handler, bytes([control_byte, data]))
    sleep(0.001)


def write_command(pi, i2c_handler, command: int):
    control_byte = 0b00000000
    pi.i2c_write_device(i2c_handler, bytes([control_byte, command]))
    sleep(0.05)


def init(pi, i2c_handler):
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
    #   - D: ディスプレイ
    #     (1) ON
    #     (0) OFF (default)
    #   - C: カーソル表示
    #     (1) ON
    #     (0) OFF (default)
    #   - B: ブリンク表示
    #     (1) ON
    #     (0) OFF (default)
    write_command(pi, i2c_handler, 0b00001100)

    # Entry Mode Set (IS=0, RE=0, SD=0)
    #   データ書き込み時のカーソルの移動方向の設定
    #   0 0 0 0 0 1 I/D S
    #   - I/D:
    #     (1) カーソルが右に移動しDDRAMアドレスがインクリメント (default)
    #     (0) カーソルが左に移動しDDRAMアドレスがデクリメント
    #   - S: ディスプレイ全体のシフト
    #     (1) I/D=1ならディスプレイ全体が右にシフト。I/D=0なら左にシフト。
    #     (0) ディスプレイのシフトを行わない (default)
    write_command(pi, i2c_handler, 0b00000110)  # シフト設定をデフォルト値に

    # Function Set (IS=0, RE=1, SD=0)
    #   機能設定
    #   0 0 0 1 * N DH RE(0) REV
    #   - N: 表示行数制御
    #     (1) 2行表示
    #     (0) 1行表示
    #   - DH: 2行高フォント制御
    #     (1) 2行分の高さで1文字を表示 (DDRAMは0x00 - 0x27まで利用可能)
    #     (0) 通常表示
    #   - RE: 拡張命令用レジスタ
    #     (1) 利用する
    #     (0) 利用しない
    #   - REV: 表示反転
    #     (1) 反転する
    #     (0) 反転しない
    write_command(pi, i2c_handler, 0b00101010)  # RE=1


    # OLED Characterization (IS=0, RE=1, SD=0)
    #   0 1 1 1 1 0 0 SD
    #   - SD: 拡張命令用レジスタ
    #     (1) 利用する
    #     (0) 利用しない
    write_command(pi, i2c_handler, 0b01111001)  # SD=1
    # IS=0, RE=1, SD=1

    # Set Contrast Control
    #   コントラスト設定。
    #   2バイトコマンドなので、このあとに輝度設定バイト(0x00 - 0xFF)を送信
    #   1 0 0 0 0 0 0 1
    write_command(pi, i2c_handler, 0b10000001)  # コントラストセット
    write_command(pi, i2c_handler, 0b11111111)  # 輝度 max

    # OLED Characterization (IS=0, RE=1, SD=0)
    #   0 1 1 1 1 0 0 SD
    #   - SD: 拡張命令用レジスタ
    #     (1) 利用する
    #     (0) 利用しない
    write_command(pi, i2c_handler, 0b01111000)  # SD=0
    # IS=0, RE=1, SD=0

    # Function Set (IS=X, RE=0, SD=0)
    #   機能設定
    #   0 0 0 1 * N DH RE(0) IS
    #   - N: 表示行数制御
    #     (1) 2行表示
    #     (0) 1行表示
    #   - DH: 2行高フォント制御
    #     (1) 2行分の高さで1文字を表示 (DDRAMは0x00 - 0x27まで利用可能)
    #     (0) 通常表示
    #   - RE: 拡張命令用レジスタ
    #     (0) 利用しない
    #   - IS: 拡張命令用レジスタ
    #     (1) 利用する
    #     (0) 利用しない
    write_command(pi, i2c_handler, 0b00101000)  # RE=0, IS=0
    # IS=0, RE=0, SD=0



def off(pi, i2c_handler):
    write_command(pi, i2c_handler, 0b01111000)  # SD=1 (OLED Characterization)
    write_command(pi, i2c_handler, 0b00101000)  # RE=0, IS=0 (Function Set)
    write_command(pi, i2c_handler, 0b00000001)  # Clear Display
    write_command(pi, i2c_handler, 0b00000010)  # Return Home
    write_command(pi, i2c_handler, 0b00001000)  # Display, cursor, blink = OFF



def disp_01(pi, i2c_handler):
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

    sleep(10)

def disp_02(pi, i2c_handler):
    """
    繰り返し表示
    ※ 17 ~ 20 文字の表示で利用
    """
    # 設定

    l1 = b"Temp  Pres Hum"  # 20byteまで保持できる
    for char in l1:
        write_data(pi, i2c_handler, char)

    ddram_addr = 0b00100000  # 2行目の先頭 (0x20)
    write_command(pi, i2c_handler, 0b10000000 | ddram_addr)  # Set DDRAM RAM Address
    l2 = b"24.34 1012 50.35"
    for ch in l2:
        write_data(pi, i2c_handler, ch)  # 0xB1 = ア
    
    while (True):
        # Cursor or Display Shift (IS=0, RE=0, SD=0)
        #   カーソル位置の移動設定
        #   0 0 0 1 S/C R/L * *
        #   - S/C: 画面とカーソルどちらをシフトするかを選択
        #     (1) 画面をシフト
        #     (0) カーソルをシフト
        #   - R/L: 左右どちらにシフトするかを選択
        #     (1) 右にシフト
        #     (0) 左にシフト
        write_command(pi, i2c_handler, 0b00011000)
        sleep(0.5)

def disp_03(pi, i2c_handler):
    """
    スクロール表示
    ※ 長文の表示で利用
    """
    l1 = b"Text:"
    for char in l1:
        write_data(pi, i2c_handler, char)
    sleep(1)

    # Entry Mode Set (IS=0, RE=0, SD=0)
    #   データ書き込み時のカーソルの移動方向の設定
    #   0 0 0 0 0 1 I/D S
    #   - I/D:
    #     (1) カーソルが右に移動しDDRAMアドレスがインクリメント (default)
    #     (0) カーソルが左に移動しDDRAMアドレスがデクリメント
    #   - S: ディスプレイ全体のシフト
    #     (1) I/D=1ならディスプレイ全体が右にシフト。I/D=0なら左にシフト。
    #     (0) ディスプレイのシフトを行わない (default)
    write_command(pi, i2c_handler, 0b00000111)


    l2 = b"If there was an error the number of bytes read will be less than zero (and will contain the error code)."
    l2 += (b" " * (len(l2) % 20))

    idx = 0
    while (True):
        for char in l2:
            if (idx % 20 == 0):  # 20文字ごとにDDRAMをリセット
                # Set DDRAM RAM Address (IS=0, RE=X, SD=0)
                #   DDRAMアドレスを設定
                #   1 N N N N N N N
                #   - N: アドレスを指定 1行目(0x00 - 0x0F) 2行目(0x20 - 0x2F)
                write_command(pi, i2c_handler, 0b10100000)  # 2行目の先頭 (0x20)

            write_data(pi, i2c_handler, char)
            sleep(0.1)
            idx += 1

def disp_04(pi, i2c_handler):
    """
    スクロール表示 (1行目固定)
    ※ 長文の表示で利用
    """
    l1 = b"Text:"
    for char in l1:
        write_data(pi, i2c_handler, char)
    sleep(1)

    # Entry Mode Set (IS=0, RE=0, SD=0)
    #   データ書き込み時のカーソルの移動方向の設定
    #   0 0 0 0 0 1 I/D S
    #   - I/D:
    #     (1) カーソルが右に移動しDDRAMアドレスがインクリメント (default)
    #     (0) カーソルが左に移動しDDRAMアドレスがデクリメント
    #   - S: ディスプレイ全体のシフト
    #     (1) I/D=1ならディスプレイ全体が右にシフト。I/D=0なら左にシフト。
    #     (0) ディスプレイのシフトを行わない (default)
    write_command(pi, i2c_handler, 0b00000111)

    write_command(pi, i2c_handler, 0b00101010)  # RE=1
    # IS=0, RE=1, SD=0

    # Double Height(4line)/Display-dot shift (IS=0, RE=1, SD=0)
    #   0 0  0 1 UD2 UD1 * DH'
    #   - UD2,UD2: あまり関係ないので 11 (default)
    #   - DH': 選択した行だけディスプレイシフトを行う設定の有効・無効
    #     (1) 有効化 (ディスプレイシフト)
    #     (0) 無効化 (スクロール) (default)
    write_command(pi, i2c_handler, 0b00011101)

    write_command(pi, i2c_handler, 0b00101001)  # RE=0, IS=1
    write_command(pi, i2c_handler, 0b00101010)  # RE=1
    # IS=1, RE=1, SD=0

    # Shift / Scroll Enable (IS=1, RE=1, SD=0)
    #   0 0 0 1 DS4/HS4 DS3/HS3 DS2/HS2 DS1/HS1
    #   - DS/HS: 1111 (default)
    #     - DS4 ~ DS1: DH'=1の場合は、行毎のディスプレイシフトを有効化
    #     - HS4 ~ HS1: DH'=0の場合は、行毎の水平スクロールを有効化
    write_command(pi, i2c_handler, 0b00010010)  # display shift enable line2

    write_command(pi, i2c_handler, 0b00101000)  # RE=0, IS=0


    try:
        l2 = b"If there was an error the number of bytes read will be less than zero (and will contain the error code)."
        l2 += (b" " * (len(l2) % 20))
        idx = 0
        while (True):
            for char in l2:
                if (idx % 20 == 0):  # 20文字ごとにDDRAMをリセット
                    # Set DDRAM RAM Address (IS=0, RE=X, SD=0)
                    #   DDRAMアドレスを設定
                    #   1 N N N N N N N
                    #   - N: アドレスを指定 1行目(0x00 - 0x0F) 2行目(0x20 - 0x2F)
                    write_command(pi, i2c_handler, 0b10100000)  # 2行目の先頭 (0x20)

                write_data(pi, i2c_handler, char)
                sleep(0.1)
                idx += 1
    finally:
        write_command(pi, i2c_handler, 0b00101010)  # RE=1
        # IS=0, RE=1, SD=0

        # Double Height(4line)/Display-dot shift (IS=0, RE=1, SD=0)
        #   0 0  0 1 UD2 UD1 * DH'
        #   - UD2,UD2: あまり関係ないので 11 (default)
        #   - DH': 選択した行だけディスプレイシフトを行う設定の有効・無効
        #     (1) 有効化 (ディスプレイシフト)
        #     (0) 無効化 (スクロール) (default)
        write_command(pi, i2c_handler, 0b00011101)

        write_command(pi, i2c_handler, 0b00101001)  # RE=0, IS=1
        write_command(pi, i2c_handler, 0b00101010)  # RE=1
        # IS=1, RE=1, SD=0

        # Shift / Scroll Enable (IS=1, RE=1, SD=0)
        #   0 0 0 1 DS4/HS4 DS3/HS3 DS2/HS2 DS1/HS1
        #   - DS/HS: 1111 (default)
        #     - DS4 ~ DS1: DH'=1の場合は、行毎のディスプレイシフトを有効化
        #     - HS4 ~ HS1: DH'=0の場合は、行毎の水平スクロールを有効化
        write_command(pi, i2c_handler, 0b00011111)  # display shift enable line2

        write_command(pi, i2c_handler, 0b00101000)  # RE=0, IS=0


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
        #disp_01(pi, i2c_handler)
        #disp_02(pi, i2c_handler)
        #disp_03(pi, i2c_handler)
        disp_04(pi, i2c_handler)
        sleep(10)
    finally:
        off(pi, i2c_handler)
        sleep(1)
        pi.i2c_close(i2c_handler)
        pi.stop()