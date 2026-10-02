# SD CID Reader

[English](README.md) | **ไทย**

โปรแกรมอ่านรีจิสเตอร์ **CID** และ **CSD** ของการ์ด SD / microSD แล้วแสดงผู้ผลิต (จับคู่ Manufacturer ID กับชื่อบริษัท), OEM ID, ชื่อรุ่น, revision, **Serial Number**, วันที่ผลิต, ผลตรวจ CRC และความจุ ผ่าน GUI ที่ใช้ได้ทั้ง Windows, Linux, macOS (สลับภาษาอังกฤษ/ไทยได้)

## ทำไมต้องใช้ฮาร์ดแวร์เพิ่ม?

**USB card reader ทั่วไปไม่ส่งค่า CID ให้ PC** เพราะชิปในตัว reader คุยโปรโตคอล SD กับการ์ดเอง แล้วแสดงการ์ดให้ระบบเห็นเป็นดิสก์ธรรมดา โปรแกรมบน Windows หรือ macOS จึงอ่าน CID ผ่าน reader แบบนี้ไม่ได้

โปรเจกต์นี้แก้ปัญหาด้วย **บอร์ด RP2040 ราคาไม่กี่สิบบาทที่ต่อกับสล็อต microSD ผ่าน SPI** firmware ขอค่า CID/CSD จากการ์ดโดยตรง แล้วส่งให้ PC ทาง USB serial เพื่อให้ GUI ถอดรหัส

| การ์ดอยู่ที่ไหน | อ่าน CID ได้ไหม |
|---|---|
| ต่อกับบอร์ด RP2040 (โปรเจกต์นี้) | ✅ ทั้ง Windows, Linux, macOS |
| ช่อง SD ในตัวเครื่อง Linux (`/sys/class/mmc_host/`) | ✅ GUI ตรวจพบอัตโนมัติ |
| USB card reader ทั่วไป | ❌ reader ไม่ส่งค่ามา ต้องนำ CID ที่ได้จากที่อื่นมาวางเอง |

## ความสามารถ

- ถอดรหัส MID → ผู้ผลิต (SanDisk, Samsung, Kingston, Lexar, Transcend ฯลฯ), OID, PNM, PRV, PSN, วันที่ผลิต, CRC7 (ช่วยเตือนเมื่อ CID เสียหายหรือถูกแก้) และความจุจาก CSD v1/v2/v3
- GUI **สลับภาษาไทย/อังกฤษได้ขณะใช้งาน** (จำค่าที่เลือกไว้)
- firmware ตรวจการเสียบ/ถอดการ์ดอัตโนมัติ และมี LED RGB บนบอร์ดบอกสถานะ
- วางค่า CID/CSD แบบ hex เพื่อถอดรหัสโดยไม่ต้องมีการ์ดก็ได้
- คัดลอกผลลัพธ์หรือบันทึกเป็น JSON มีโปรแกรมถอดรหัสแบบ command line มาด้วย

## โครงสร้างโปรเจกต์

```
firmware/            firmware ภาษา C สำหรับ RP2040 (pico-sdk) และไฟล์ .uf2 ที่ build แล้ว
firmware/micropython ทางเลือกแบบ MicroPython (ใช้ได้กับบอร์ด Pico/RP2040 ทั่วไป)
gui/sdcid_gui.py     โปรแกรม GUI (ไฟล์เดียว)
tools/sdcid.py       โปรแกรมถอดรหัสแบบ command line
docs/wiring.md       บันทึกการต่อสาย
```

## ฮาร์ดแวร์ที่ใช้

- Waveshare **RP2040‑Zero** (โค้ด LED เขียนสำหรับบอร์ดนี้ แต่ Raspberry Pi Pico ก็ใช้ได้ เพียงแต่ไม่ใช้ LED)
- สล็อตหรือโมดูล microSD ที่เข้าถึงขาได้ ใช้ลอจิก 3.3 V
- ลวดเส้นเล็ก หัวแร้ง และตัวเก็บประจุ 10 µF (ไม่บังคับ) คร่อม 3V3/GND ใกล้สล็อต

### การต่อสาย (SPI0)

| ขา microSD | สัญญาณ | RP2040‑Zero |
|---|---|---|
| 7 (DAT0) | MISO | **GP0** |
| 2 (CD/DAT3) | CS | **GP1** |
| 5 (CLK) | SCK | **GP2** |
| 3 (CMD) | MOSI | **GP3** |
| 4 (VDD) | 3.3 V | **3V3** |
| 6 (VSS) | GND | **GND** |
| 1 (DAT2), 8 (DAT1) | ไม่ใช้ | ปล่อยว่าง (หรือดึงขึ้น 3V3 ด้วย 10 kΩ) |

> ⚠️ **ตรวจ VDD/VSS ให้แน่ใจก่อนเสียบการ์ด** ถ้าสลับกันการ์ดอาจพัง ให้วัดต่อเนื่องด้วยมัลติมิเตอร์ทีละเส้น และลองกับการ์ดเก่าก่อน ดู [docs/wiring.md](docs/wiring.md)

## เริ่มต้นใช้งาน

### 1. Flash firmware

1. กดปุ่ม **BOOT** บน RP2040‑Zero ค้างไว้ แล้วเสียบ USB เข้า PC
2. จะมีไดรฟ์ชื่อ `RPI-RP2` โผล่ขึ้นมา ให้ลากไฟล์ `firmware/prebuilt/sdcid_reader_rp2040zero.uf2` ใส่
3. บอร์ดรีสตาร์ตเอง Windows 10/11 จะเห็นเป็นพอร์ต COM (ไม่ต้องลงไดรเวอร์) Linux เป็น `/dev/ttyACM0` macOS เป็น `/dev/cu.usbmodem*`

LED เป็น **น้ำเงิน** ตอนรอการ์ด **เขียว** เมื่ออ่านสำเร็จ และ **แดง** เมื่อผิดพลาด

### 2. เปิด GUI

ต้องมี Python 3.7+ พร้อม tkinter และ `pyserial` สำหรับคุยกับบอร์ด

```bash
pip install pyserial
python gui/sdcid_gui.py
```

เลือกพอร์ตของบอร์ด (อุปกรณ์ของ Raspberry Pi จะอยู่บนสุด หรือพิมพ์เอง เช่น `COM5`) แล้วกด **อ่านจากบอร์ด** ใช้ช่อง **Language / ภาษา** มุมขวาบนเพื่อสลับภาษา

#### ติดตั้ง Python / tkinter

| ระบบ | คำสั่ง |
|---|---|
| Windows | ติดตั้ง Python จาก <https://www.python.org/downloads/> (มี tkinter อยู่แล้ว ติ๊ก *Add python.exe to PATH*) |
| macOS | `brew install python-tk` (หรือใช้ตัวติดตั้งจาก python.org) |
| Debian / Ubuntu | `sudo apt install python3 python3-tk python3-pip` |
| Fedora | `sudo dnf install python3 python3-tkinter` |

> ให้ติดตั้ง **`pyserial`** ไม่ใช่ `serial` (คนละแพ็กเกจ)

### 3. ใช้งานโดยไม่มีบอร์ด

- Linux ที่มีช่อง SD ในตัวเครื่อง: กด **อ่านการ์ดอัตโนมัติ**
- ทุกระบบ: วาง CID (และ CSD ถ้ามี) เป็น hex 32 ตัว แล้วกด **ถอดรหัส**
- command line: `python tools/sdcid.py --cid <hex 32 ตัว> [--csd <hex 32 ตัว>] [--json]`

## โปรโตคอล serial

USB CDC serial แบบบรรทัดข้อความ:

| ทิศทาง | ข้อความ | ความหมาย |
|---|---|---|
| PC → บอร์ด | `r` | สั่งอ่านการ์ดทันที |
| บอร์ด → PC | `CID=<hex 32 ตัว>` / `CSD=<hex 32 ตัว>` | ค่ารีจิสเตอร์ (ส่งอัตโนมัติเมื่อเสียบการ์ดด้วย) |
| บอร์ด → PC | `ERR=<รหัส>` | `NO_CARD`, `BAD_CMD8`, `INIT_TIMEOUT`, `CID_FAIL` |
| บอร์ด → PC | `REMOVED` | ถอดการ์ดออกแล้ว |

ทดสอบได้ด้วยโปรแกรม serial terminal ทั่วไป (PuTTY, Tera Term, `screen /dev/ttyACM0`)

## Build firmware จากซอร์ส

ต้องมี `cmake`, `gcc-arm-none-eabi` และ [pico‑sdk](https://github.com/raspberrypi/pico-sdk) 2.x

```bash
git clone --depth 1 -b 2.1.1 https://github.com/raspberrypi/pico-sdk ~/pico-sdk
git -C ~/pico-sdk submodule update --init --depth 1 lib/tinyusb

cd firmware
cmake -B build -DPICO_SDK_PATH=$HOME/pico-sdk
cmake --build build -j4
# ได้ build/sdcid_reader.uf2
```

`CMakeLists.txt` ตั้ง `PICO_BOARD=waveshare_rp2040_zero` ถ้าใช้ Raspberry Pi Pico ให้เปลี่ยนเป็น `pico` และมี GitHub Actions (`.github/workflows/build-firmware.yml`) build ไฟล์ UF2 ให้ทุกครั้งที่ push

**อยากใช้ MicroPython?** ติดตั้ง MicroPython ลงบอร์ด แล้วบันทึก `firmware/micropython/main.py` เป็น `main.py` ใช้โปรโตคอลเดียวกัน (แต่ไม่มี LED และไม่ตรวจการ์ดอัตโนมัติ)

## โครงสร้าง CID (อ้างอิง)

| บิต | ฟิลด์ | ความหมาย |
|---|---|---|
| 127:120 | MID | รหัสผู้ผลิต |
| 119:104 | OID | OEM/Application ID (ตัวอักษร ASCII 2 ตัว) |
| 103:64 | PNM | ชื่อรุ่น (ASCII 5 ตัว) |
| 63:56 | PRV | revision (BCD แบบ `major.minor`) |
| 55:24 | PSN | Serial Number 32 บิต |
| 19:8 | MDT | วันที่ผลิต (ปีนับจาก 2000, เดือน) |
| 7:1 | CRC7 | checksum |

## แก้ปัญหา

| อาการ | ตรวจอะไร |
|---|---|
| LED ค้างสีน้ำเงิน, `ERR=NO_CARD` | สายต่อ (MISO/MOSI สลับกันบ่อย), เสียบการ์ดแน่นหรือยัง, มีไฟ 3.3 V ที่สล็อตไหม |
| `ERR=INIT_TIMEOUT` | ไม่ใช่การ์ด SD (เช่น MMC/eMMC) หรือสายหลวม |
| GUI ไม่มีพอร์ตให้เลือก | ดู Device Manager → *Ports (COM & LPT)*, ลองเปลี่ยนสาย USB (บางเส้นชาร์จอย่างเดียว) |
| "บอร์ดไม่ตอบกลับ" | ยังไม่ได้ flash firmware หรือมีโปรแกรมอื่น (Thonny, terminal) จองพอร์ตอยู่ |
| ช่องพอร์ตบอกว่าไม่มี pyserial | `pip install pyserial` |
| ผู้ผลิตขึ้น *ไม่รู้จัก* | MID ยังไม่อยู่ในตาราง ช่วยส่ง PR เพิ่มได้ |

## ข้อจำกัด

- รองรับเฉพาะการ์ด SD / microSD (SDSC, SDHC, SDXC) **ไม่รองรับ eMMC / MMC รุ่นเก่า**
- CID **ไม่ใช่หลักฐานว่าการ์ดแท้**: การ์ดปลอมอาจลอก CID หรือปลอมค่าได้ CRC ไม่ตรงเป็นเพียงข้อสังเกต ไม่ใช่คำตัดสิน
- ตารางผู้ผลิตมาจากชุมชนและยังไม่ครบ
- firmware ทดสอบกับ RP2040‑Zero + สล็อต microSD ที่ต่อสายเอง บอร์ดอื่นอาจต้องแก้ขาใน `firmware/main.c`

## ร่วมพัฒนา

ยินดีรับ Issue และ PR โดยเฉพาะ MID ใหม่ (พร้อมแหล่งอ้างอิง), บอร์ดอื่น และภาษาใหม่ (เพิ่มบล็อกภาษาใน `STR` ของ `gui/sdcid_gui.py`)

## สัญญาอนุญาต

[MIT](LICENSE) ส่วน `firmware/pico_sdk_import.cmake` มาจาก pico‑sdk ของ Raspberry Pi (BSD‑3‑Clause)
