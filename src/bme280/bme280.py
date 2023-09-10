import time
from typing import Union
import pigpio

def int_to_binary(n: int, bits: int = 8):
    return ''.join([str(n >> i & 1 ) for i in reversed(range(0, bits))])

def bytes_to_binary(data: Union[bytearray,bytes]):
    return ','.join([int_to_binary(byte) for byte in data])

def write(pi, spi_handler, register: int, data: int):
    register_bytes = (register & 0b01111111).to_bytes(1, "big")
    cnt, read_data = pi.spi_xfer(spi_handler, register_bytes)
    print(f"register_bytes: register={int_to_binary(register)}, cnt={cnt}, read_data={int_to_binary(int.from_bytes(read_data, 'big'))}")
    data_bytes = data.to_bytes(1, "big")
    cnt, read_data = pi.spi_xfer(spi_handler, data_bytes)
    print(f"register_bytes: data={int_to_binary(data)}, cnt={cnt}, read_data={int_to_binary(int.from_bytes(read_data, 'big'))}")

#def read(pi, spi_handler, reg_address: int , num_bytes: int):
#    data = []
#    addr = reg_address | 0b10000000;
#    pi.spi_xfer(spi_handler, addr)
#    spi_handler()
#    SPI.transfer(addr);
#    for (int i = 0; i < numBytes; i++) {
#        data[i] = SPI.transfer(0x00);
#    }

def main(pi, spi_handler):
    osrs_t = 1    # Temperature oversampling x 1
    osrs_p = 1    # Pressure oversampling x 1
    osrs_h = 1    # Humidity oversampling x 1
    mode = 3      # Normal mode
    t_sb = 5      # Tstandby 1000ms
    filter = 0    # Filter off 
    spi3w_en = 0  # 3-wire SPI Disable

    ctrl_meas_reg = (osrs_t << 5) | (osrs_p << 2) | mode
    config_reg    = (t_sb << 5) | (filter << 2) | spi3w_en
    ctrl_hum_reg  = osrs_h

    pi.write(spi_handler, 0xF2, ctrl_hum_reg)
    pi.write(spi_handler, 0xF4, ctrl_meas_reg)
    pi.write(spi_handler, 0xF5, config_reg)

    while True:
        write_data = 0b11111010 << 8
        write_data = write_data.to_bytes(2, "big")
        cnt, read_data = pi.spi_xfer(spi_handler, write_data)
        if cnt != 2:
            print("[error] skip.")
            time.sleep(1)
            continue
        value = int.from_bytes(read_data, "big") & 0b1111111111  # 10ビットを値として取り出す
        print(f"w: {bytes_to_binary(write_data)}")
        print(f"r: {bytes_to_binary(read_data)}")
        print(f"value: {value}")
        time.sleep(1)



if __name__ == "__main__":
    pi = pigpio.pi()
    if not pi.connected:
        raise Exception("pigpio connection faild...")

    # オプション (http://abyz.me.uk/rpi/pigpio/python.html#spi_open)
    # 21 20 19 18 17 16 15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
    # b  b  b  b  b  b  R  T  n  n  n  n  W  A u2 u1 u0 p2 p1 p0  m  m
    # mm: SPIモード
    # A: メインSPI(0), AuxSPI(1) どちらを利用するか選択
    # W: 3線のSPIを利用するなら(1)、4線なら(0) (メインSPIでしか利用できない)
    # あとは使いどころあるのかよくわからん、、、
    SPI_MODE = 0b11  # SPIモード0を設定。アイドル時のクロックはHIGH(CPOL=1)、クロックがLOWになるときにデータをサンプリング(CPHA=1)
    OPTION = 0b0 | SPI_MODE
    CLOCK_SPEED = 1_000_000  # 1MHz
    SPI_CHANNEL = 0
    spi_handler = pi.spi_open(SPI_CHANNEL, CLOCK_SPEED, OPTION)

    try:
        main(pi, spi_handler)

    finally:
        pi.spi_close(spi_handler)
        pi.stop()
