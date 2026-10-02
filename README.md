# SD CID Reader

**English** | [ไทย](README.th.md)

Read the **CID** (card identification) and **CSD** registers of an SD / microSD card — manufacturer ID mapped to a company name, OEM ID, product name, revision, **serial number**, manufacture date, CRC check and capacity — and show them in a small cross‑platform GUI (Windows, Linux, macOS; English / Thai).

## Why does this need extra hardware?

A normal **USB card reader hides the CID** from the PC: its controller talks the SD protocol to the card by itself and only exposes the card as a plain disk. So no program on Windows or macOS can read the CID through such a reader.

This project works around that with a ~US$2 **RP2040 board wired to a microSD slot over SPI**. The firmware asks the card for its CID/CSD directly and sends the values to the PC over USB serial, where the GUI decodes them.

| Where the card is | Can the CID be read? |
|---|---|
| Wired to the RP2040 board (this project) | ✅ on Windows, Linux, macOS |
| Built‑in SD slot on Linux (`/sys/class/mmc_host/`) | ✅ GUI auto‑detects |
| Ordinary USB card reader | ❌ not exposed by the reader — paste a CID you got elsewhere |

## Features

- Decodes MID → manufacturer (SanDisk, Samsung, Kingston, Lexar, Transcend …), OID, PNM, PRV, PSN, manufacture date, CRC7 (flags corrupt/altered CIDs), and capacity from CSD v1/v2/v3
- GUI in **English and Thai**, switchable at runtime (choice is remembered)
- Firmware auto‑detects card insertion/removal; on‑board RGB LED shows the state
- Paste any CID/CSD hex to decode it offline
- Copy results or save them as JSON; command‑line decoder included

## Repository layout

```
firmware/            C firmware for RP2040 (pico-sdk) + prebuilt .uf2
firmware/micropython MicroPython alternative (any Pico / RP2040 board)
gui/sdcid_gui.py     the GUI (single file)
tools/sdcid.py       command-line decoder
docs/wiring.md       wiring notes
```

## Hardware

- Waveshare **RP2040‑Zero** (the firmware's LED code targets it; a Raspberry Pi Pico also works — the LED is simply not used)
- A microSD slot / breakout with accessible pins, 3.3 V logic
- Thin wire, soldering iron. Optional: 10 µF capacitor across 3V3/GND near the slot

### Wiring (SPI0)

| microSD pin | Signal | RP2040‑Zero |
|---|---|---|
| 7 (DAT0) | MISO | **GP0** |
| 2 (CD/DAT3) | CS | **GP1** |
| 5 (CLK) | SCK | **GP2** |
| 3 (CMD) | MOSI | **GP3** |
| 4 (VDD) | 3.3 V | **3V3** |
| 6 (VSS) | GND | **GND** |
| 1 (DAT2), 8 (DAT1) | unused | leave open (or 10 kΩ pull‑up to 3V3) |

> ⚠️ **Double‑check VDD/VSS before inserting a card.** Swapping them can destroy the card. Verify each wire with a multimeter's continuity mode first, and try a spare card initially. See [docs/wiring.md](docs/wiring.md).

## Quick start

### 1. Flash the firmware

1. Hold the **BOOT** button on the RP2040‑Zero and plug it into the PC via USB.
2. A drive named `RPI-RP2` appears. Copy `firmware/prebuilt/sdcid_reader_rp2040zero.uf2` onto it.
3. The board reboots. Windows 10/11 shows it as a COM port (no driver needed); Linux as `/dev/ttyACM0`; macOS as `/dev/cu.usbmodem*`.

The LED is **blue** while waiting for a card, **green** after a successful read, **red** on error.

### 2. Run the GUI

Requirements: Python 3.7+ with tkinter, plus `pyserial` for the board.

```bash
pip install pyserial
python gui/sdcid_gui.py
```

Pick the board's serial port (Raspberry Pi devices are listed first, or type e.g. `COM5`), then press **Read from board**. Use the **Language** box at the top right to switch between English and Thai.

#### Installing Python / tkinter

| OS | Command |
|---|---|
| Windows | Install Python from <https://www.python.org/downloads/> (tkinter is included; tick *Add python.exe to PATH*) |
| macOS | `brew install python-tk` (or the python.org installer) |
| Debian / Ubuntu | `sudo apt install python3 python3-tk python3-pip` |
| Fedora | `sudo dnf install python3 python3-tkinter` |

> Install **`pyserial`**, not `serial` (a different package).

### 3. Without the board

- Linux with a built‑in SD slot: press **Auto‑detect card**.
- Anywhere: paste a CID (and optionally CSD) as 32 hex characters and press **Decode**.
- Command line: `python tools/sdcid.py --cid <32 hex> [--csd <32 hex>] [--json]`

## Serial protocol

USB CDC serial, line based:

| Direction | Text | Meaning |
|---|---|---|
| host → board | `r` | read the card now |
| board → host | `CID=<32 hex>` / `CSD=<32 hex>` | register values (also sent automatically on insertion) |
| board → host | `ERR=<code>` | `NO_CARD`, `BAD_CMD8`, `INIT_TIMEOUT`, `CID_FAIL` |
| board → host | `REMOVED` | the card was taken out |

You can test it with any serial terminal (PuTTY, Tera Term, `screen /dev/ttyACM0`).

## Building the firmware from source

Needs `cmake`, `gcc-arm-none-eabi`, and [pico‑sdk](https://github.com/raspberrypi/pico-sdk) 2.x.

```bash
git clone --depth 1 -b 2.1.1 https://github.com/raspberrypi/pico-sdk ~/pico-sdk
git -C ~/pico-sdk submodule update --init --depth 1 lib/tinyusb

cd firmware
cmake -B build -DPICO_SDK_PATH=$HOME/pico-sdk
cmake --build build -j4
# -> build/sdcid_reader.uf2
```

`CMakeLists.txt` sets `PICO_BOARD=waveshare_rp2040_zero`; change it to `pico` for a Raspberry Pi Pico. A GitHub Actions workflow (`.github/workflows/build-firmware.yml`) builds the UF2 on every push.

**MicroPython instead?** Install MicroPython on the board and save `firmware/micropython/main.py` as `main.py`. It speaks the same protocol (without LED and auto‑detect).

## CID layout (reference)

| Bits | Field | Meaning |
|---|---|---|
| 127:120 | MID | manufacturer ID |
| 119:104 | OID | OEM/application ID (2 ASCII chars) |
| 103:64 | PNM | product name (5 ASCII chars) |
| 63:56 | PRV | revision (BCD, `major.minor`) |
| 55:24 | PSN | 32‑bit serial number |
| 19:8 | MDT | manufacture date (year offset from 2000, month) |
| 7:1 | CRC7 | checksum |

## Troubleshooting

| Symptom | Check |
|---|---|
| LED stays blue, `ERR=NO_CARD` | wiring (MISO/MOSI swapped is common), card fully seated, 3.3 V present at the slot |
| `ERR=INIT_TIMEOUT` | not an SD card (e.g. MMC/eMMC), or a poor connection |
| GUI port list is empty | Device Manager → *Ports (COM & LPT)*; try another USB cable (some are charge‑only) |
| "Board did not respond" | firmware not flashed, or another program (Thonny, a terminal) holds the port |
| Port box says pyserial missing | `pip install pyserial` |
| Manufacturer shows *Unknown* | MID isn't in the table yet — please open a PR |

## Limitations

- SD / microSD cards only (SDSC, SDHC, SDXC); **no eMMC / old MMC** support.
- The CID is **not proof of authenticity**: counterfeit cards can carry copied or forged CIDs. A CRC mismatch is a hint, not a verdict.
- The manufacturer table is community‑maintained and incomplete.
- The firmware was tested on a hand‑wired RP2040‑Zero + microSD slot; other boards may need pin changes in `firmware/main.c`.

## Contributing

Issues and PRs are welcome — especially new MID entries (with a source), other boards, and translations (add a language block to `STR` in `gui/sdcid_gui.py`).

## License

[MIT](LICENSE). `firmware/pico_sdk_import.cmake` comes from the Raspberry Pi pico‑sdk (BSD‑3‑Clause).
