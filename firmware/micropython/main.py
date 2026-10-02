"""
MicroPython alternative to the C firmware (works on a Raspberry Pi Pico / RP2040-Zero).
Save it on the board as main.py (e.g. with Thonny).

Wiring (SPI0) - same as the C firmware:
  SD DAT0 (MISO) -> GP0    SD CD/DAT3 (CS) -> GP1
  SD CLK         -> GP2    SD CMD (MOSI)   -> GP3
  SD VDD -> 3V3            SD VSS -> GND

Protocol: send "r" over USB serial; the board answers
  CID=<32 hex> / CSD=<32 hex>   or   ERR=<NO_CARD|BAD_CMD8|INIT_TIMEOUT|CID_FAIL>
(No LED and no automatic card detection in this version.)
"""
import sys
import time
from machine import Pin, SPI

cs = Pin(1, Pin.OUT, value=1)
spi = SPI(0, baudrate=400000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(0))
Pin(0, Pin.IN, Pin.PULL_UP)  # keep MISO from floating


def send_cmd(cmd, arg=0, crc=0xFF):
    cs(0)
    spi.write(bytes([0x40 | cmd, (arg >> 24) & 0xFF, (arg >> 16) & 0xFF,
                     (arg >> 8) & 0xFF, arg & 0xFF, crc]))
    for _ in range(16):
        r = spi.read(1, 0xFF)[0]
        if r != 0xFF:
            return r
    return 0xFF


def end():
    cs(1)
    spi.write(b"\xff")


def init_card():
    cs(1)
    spi.write(b"\xff" * 10)
    for _ in range(5):
        r = send_cmd(0, 0, 0x95)
        end()
        if r == 0x01:
            break
    else:
        return "NO_CARD"
    r = send_cmd(8, 0x1AA, 0x87)
    v2 = False
    if r == 0x01:
        resp = spi.read(4, 0xFF)
        end()
        if resp[2] != 0x01 or resp[3] != 0xAA:
            return "BAD_CMD8"
        v2 = True
    else:
        end()
    deadline = time.ticks_add(time.ticks_ms(), 2000)
    while True:
        send_cmd(55)
        end()
        r = send_cmd(41, 0x40000000 if v2 else 0)
        end()
        if r == 0x00:
            return None
        if time.ticks_diff(deadline, time.ticks_ms()) < 0:
            return "INIT_TIMEOUT"
        time.sleep_ms(10)


def read_reg(cmd):
    if send_cmd(cmd) != 0x00:
        end()
        return None
    for _ in range(5000):
        if spi.read(1, 0xFF)[0] == 0xFE:
            break
    else:
        end()
        return None
    data = spi.read(16, 0xFF)
    spi.read(2, 0xFF)
    end()
    return bytes(data)


def hexs(b):
    return "".join("%02x" % x for x in b)


def do_read():
    err = init_card()
    if err:
        print("ERR=" + err)
        return
    cid, csd = read_reg(10), read_reg(9)
    if cid is None:
        print("ERR=CID_FAIL")
        return
    print("CID=" + hexs(cid))
    if csd is not None:
        print("CSD=" + hexs(csd))


print("READY")
while True:
    line = sys.stdin.readline()
    if not line:
        time.sleep_ms(50)
        continue
    if line.strip().lower() == "r":
        do_read()
