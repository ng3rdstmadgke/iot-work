# ■ 環境構築

```bash
# ラズパイの設定
sudo raspi-config nonint do_ssh 0  # ssh有効化
sudo raspi-config nonint do_spi 0  # SPI通信有効化
sudo raspi-config nonint do_i2c 0  # I2C通信有効化
sudo raspi-config nonint do_serial 0  # シリアル通信有効化
sudo raspi-config nonint do_camera 0  # カメラ有効化 (現状使ってないけど一応)
sudo raspi-config nonint do_rgpio 0  # リモートでのGPIO操作を有効化 (現状使ってないけど一応)

# 設定の確認
sudo raspi-config nonint get_ssh
sudo raspi-config nonint get_spi
sudo raspi-config nonint get_i2c
sudo raspi-config nonint get_serial
sudo raspi-config nonint get_camera
sudo raspi-config nonint get_rgpio

# pigpioのインストール
sudo apt update
sudo apt install pigpio

# pigpioデーモン起動
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# --- --- --- pigpiodの起動コマンドをいじりたい人は --- --- ---
# vim で編集したいので
sudo update-alternatives --set editor /usr/bin/vim.basic

# pigpiodの起動オプション
pigpiod -h

# ユニットファイルの編集
sudo systemctl edit pigpiod
# --- --- --- --- --- --- --- --- --- --- --- --- --- ---

# ライブラリインストール
python -m venv .venv
pip install -r requirements.txt
```

# コマンド実行

```bash
# ヘルプ
./bin/cli --help

# 温度センサー
./bin/cli temp
```

# 利用しているライブラリ

- [pigpio](https://pypi.org/project/pigpio/)
  - Cライブラリによるpigpio daemonというデーモン経由でGPIOを操作するらしい
  - [Pythonインターフェース](http://abyz.me.uk/rpi/pigpio/python.html)
- [wiringpi](https://pypi.org/project/wiringpi/)
  開発中止?