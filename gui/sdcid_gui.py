#!/usr/bin/env python3
"""
sdcid_gui.py - SD / microSD CID reader and decoder (GUI, English / Thai)

Runs on Windows, Linux and macOS with plain Python 3.7+ and tkinter.
Optional: `pip install pyserial` to read the card through the RP2040 board.

    python3 sdcid_gui.py
"""
import glob
import json
import locale
import os
import platform
import re
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:  # needed only for the RP2040 / Pico serial reader
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".sdcid_gui.json")

# --------------------------------------------------------------------------
# Manufacturer ID (MID) table for SD cards
# --------------------------------------------------------------------------
MANUFACTURERS = {
    0x01: "Panasonic",
    0x02: "Toshiba / Kioxia",
    0x03: "SanDisk (Western Digital)",
    0x06: "Ritek",
    0x09: "ATP Electronics",
    0x12: "Patriot Memory",
    0x13: "Kingmax",
    0x15: "Samsung (eMMC)",
    0x1B: "Samsung",
    0x1D: "ADATA",
    0x1F: "Kingston (Phison OEM)",
    0x27: "Phison",
    0x28: "Lexar (Longsys)",
    0x31: "Silicon Power",
    0x41: "Kingston",
    0x6F: "STMicroelectronics",
    0x74: "Transcend",
    0x76: "Patriot Memory",
    0x82: "Sony / Gigastone / Jiaelec",
    0x9C: "Angelbird / Hoodman / Sony",
}

FIELD_ORDER = [
    "manufacturer_name", "manufacturer_id", "oem_application_id", "product_name",
    "product_revision", "serial_number_hex", "serial_number_dec", "manufacture_date",
    "crc7_stored", "crc7_calculated", "crc_ok", "csd_version", "capacity_gb",
    "capacity_gib", "capacity_bytes", "type", "device", "cid_hex",
]

# --------------------------------------------------------------------------
# Translations
# --------------------------------------------------------------------------
STR = {
    "en": {
        "title": "SD / microSD CID Reader",
        "grp_auto": "Read from this computer",
        "btn_auto": "Auto-detect card",
        "grp_manual": "Decode from hex (works everywhere, including USB readers)",
        "lbl_cid": "CID (32 hex)",
        "lbl_csd": "CSD (32 hex)",
        "btn_decode": "Decode",
        "hint_csd": "* CSD is optional - add it to calculate the capacity",
        "grp_pico": "Read from RP2040 / Pico board (USB serial)",
        "lbl_port": "Port",
        "btn_refresh": "Refresh",
        "btn_pico": "Read from board",
        "grp_result": "Result",
        "col_field": "Field",
        "col_value": "Value",
        "btn_copy": "Copy result",
        "btn_save": "Save as JSON",
        "btn_clear": "Clear",
        "status_ready": "Ready",
        "status_reading": "Reading...",
        "status_error": "Error",
        "status_nocard": "No card found",
        "status_cards": "{n} card(s) found",
        "status_os_only": "Only OS-level info is available (not the real CID). "
                          "Enter the CID manually to decode it.",
        "status_decoded": "Decoded successfully",
        "status_copied": "Copied to clipboard",
        "status_saved": "Saved to {path}",
        "status_pico_reading": "Reading from board...",
        "status_pico_ok": "Read from board successfully",
        "status_pico_fail": "Failed to read from board",
        "dlg_error": "Error",
        "dlg_invalid": "Invalid value",
        "dlg_nodata_title": "No data",
        "dlg_nodata_msg": "Could not read card info from this computer.\n\n"
                          "A USB card reader does not pass the CID register on to the OS. "
                          "Use the built-in SD slot (Linux), the RP2040 board, "
                          "or enter the CID manually.",
        "dlg_need_pyserial_title": "pyserial required",
        "dlg_need_pyserial_msg": "Run:  pip install pyserial\nthen restart the program.",
        "pyserial_missing": "(pyserial not installed: pip install pyserial)",
        "dlg_noport_title": "No port",
        "dlg_noport_msg": "No serial port found.\nCheck Device Manager > Ports (COM & LPT), "
                          "then type the port name (e.g. COM5) into the box or press Refresh.",
        "dlg_pico_fail": "Could not read from the board",
        "generic_info": "General info",
        "unknown_mfr": "Unknown (not in table)",
        "crc_yes": "OK",
        "crc_no": "Mismatch (CID may be corrupt or altered)",
        "hex_len_error": "{name} must be 32 hex characters (16 bytes), got {n}",
        "err_unknown": "Unknown error",
        "err_no_card": "No card found (CMD0 got no reply). Check the wiring and card seating.",
        "err_bad_cmd8": "Unexpected reply to CMD8.",
        "err_init_timeout": "Card initialisation timed out (ACMD41). It may not be an SD card.",
        "err_cid_fail": "Could not read the CID register.",
        "err_no_reply": "The board did not respond. Make sure the firmware is flashed and "
                        "no other program (Thonny, a terminal...) is holding the port.",
        "note_os_windows": "Disk-level info from Windows (not the real CID)",
        "note_os_macos": "Info from system_profiler (not the real CID)",
        "f_manufacturer_name": "Manufacturer",
        "f_manufacturer_id": "Manufacturer ID (MID)",
        "f_oem_application_id": "OEM / Application ID (OID)",
        "f_product_name": "Product name (PNM)",
        "f_product_revision": "Revision (PRV)",
        "f_serial_number_hex": "Serial number (hex)",
        "f_serial_number_dec": "Serial number (dec)",
        "f_manufacture_date": "Manufacture date (YYYY-MM)",
        "f_crc7_stored": "CRC7 (stored)",
        "f_crc7_calculated": "CRC7 (calculated)",
        "f_crc_ok": "CRC check",
        "f_csd_version": "CSD version",
        "f_capacity_gb": "Capacity (GB, decimal)",
        "f_capacity_gib": "Capacity (GiB, binary)",
        "f_capacity_bytes": "Capacity (bytes)",
        "f_type": "Card type",
        "f_device": "Device (sysfs)",
        "f_cid_hex": "CID (hex)",
        "f_note": "Note",
    },
    "th": {
        "title": "SD / microSD CID Reader",
        "grp_auto": "อ่านจากเครื่องนี้",
        "btn_auto": "อ่านการ์ดอัตโนมัติ",
        "grp_manual": "ถอดรหัสจากค่า hex (ใช้ได้ทุกระบบ รวมถึงเมื่อใช้ USB reader)",
        "lbl_cid": "CID (32 hex)",
        "lbl_csd": "CSD (32 hex)",
        "btn_decode": "ถอดรหัส",
        "hint_csd": "* CSD ไม่บังคับ ใส่เพื่อคำนวณความจุ",
        "grp_pico": "อ่านจากบอร์ด RP2040 / Pico (USB serial)",
        "lbl_port": "พอร์ต",
        "btn_refresh": "รีเฟรช",
        "btn_pico": "อ่านจากบอร์ด",
        "grp_result": "ผลลัพธ์",
        "col_field": "รายการ",
        "col_value": "ค่า",
        "btn_copy": "คัดลอกผลลัพธ์",
        "btn_save": "บันทึกเป็น JSON",
        "btn_clear": "ล้าง",
        "status_ready": "พร้อมใช้งาน",
        "status_reading": "กำลังอ่านข้อมูล...",
        "status_error": "เกิดข้อผิดพลาด",
        "status_nocard": "ไม่พบการ์ด",
        "status_cards": "พบการ์ด {n} ใบ",
        "status_os_only": "ได้เฉพาะข้อมูลระดับ OS ไม่ใช่ CID จริง ให้ป้อน CID เองเพื่อถอดรหัส",
        "status_decoded": "ถอดรหัสสำเร็จ",
        "status_copied": "คัดลอกแล้ว",
        "status_saved": "บันทึกที่ {path}",
        "status_pico_reading": "กำลังอ่านจากบอร์ด...",
        "status_pico_ok": "อ่านจากบอร์ดสำเร็จ",
        "status_pico_fail": "อ่านจากบอร์ดไม่สำเร็จ",
        "dlg_error": "ผิดพลาด",
        "dlg_invalid": "ค่าไม่ถูกต้อง",
        "dlg_nodata_title": "ไม่พบข้อมูล",
        "dlg_nodata_msg": "อ่านข้อมูลการ์ดจากเครื่องนี้ไม่ได้\n\n"
                          "USB card reader ไม่ส่งค่า CID มาให้ระบบ "
                          "ลองใช้ช่อง SD ในตัวเครื่อง (Linux) บอร์ด RP2040 "
                          "หรือป้อนค่า CID เอง",
        "dlg_need_pyserial_title": "ต้องติดตั้ง pyserial",
        "dlg_need_pyserial_msg": "รันคำสั่ง:  pip install pyserial\nแล้วเปิดโปรแกรมใหม่",
        "pyserial_missing": "(ยังไม่ได้ติดตั้ง pyserial: pip install pyserial)",
        "dlg_noport_title": "ไม่พบพอร์ต",
        "dlg_noport_msg": "ไม่พบพอร์ต serial\nตรวจใน Device Manager > Ports (COM & LPT) "
                          "แล้วพิมพ์ชื่อพอร์ต เช่น COM5 ลงในช่อง หรือกด 'รีเฟรช'",
        "dlg_pico_fail": "อ่านจากบอร์ดไม่สำเร็จ",
        "generic_info": "ข้อมูลทั่วไป",
        "unknown_mfr": "ไม่รู้จัก (ไม่อยู่ในตาราง)",
        "crc_yes": "ถูกต้อง",
        "crc_no": "ไม่ตรง (CID อาจผิด/ถูกแก้)",
        "hex_len_error": "{name} ต้องเป็น hex 32 ตัว (16 ไบต์) แต่ได้ {n} ตัว",
        "err_unknown": "ข้อผิดพลาดที่ไม่ทราบสาเหตุ",
        "err_no_card": "ไม่พบการ์ด (CMD0 ไม่ตอบ) ตรวจสายและการเสียบการ์ด",
        "err_bad_cmd8": "CMD8 ตอบผิดปกติ",
        "err_init_timeout": "การ์ดเริ่มต้นไม่สำเร็จ (ACMD41 timeout) อาจไม่ใช่การ์ด SD",
        "err_cid_fail": "อ่านรีจิสเตอร์ CID ไม่สำเร็จ",
        "err_no_reply": "บอร์ดไม่ตอบกลับ ตรวจว่า flash firmware แล้ว "
                        "และไม่มีโปรแกรมอื่น (Thonny, terminal ฯลฯ) จองพอร์ตไว้",
        "note_os_windows": "ข้อมูลระดับดิสก์จาก Windows (ไม่ใช่ CID จริง)",
        "note_os_macos": "ข้อมูลจาก system_profiler (ไม่ใช่ CID จริง)",
        "f_manufacturer_name": "ผู้ผลิต (บริษัท)",
        "f_manufacturer_id": "Manufacturer ID (MID)",
        "f_oem_application_id": "OEM / Application ID (OID)",
        "f_product_name": "ชื่อรุ่น (PNM)",
        "f_product_revision": "Revision (PRV)",
        "f_serial_number_hex": "Serial Number (hex)",
        "f_serial_number_dec": "Serial Number (dec)",
        "f_manufacture_date": "วันที่ผลิต (ปี-เดือน)",
        "f_crc7_stored": "CRC7 ในการ์ด",
        "f_crc7_calculated": "CRC7 ที่คำนวณ",
        "f_crc_ok": "ตรวจ CRC",
        "f_csd_version": "CSD Version",
        "f_capacity_gb": "ความจุ (GB, ฐาน 10)",
        "f_capacity_gib": "ความจุ (GiB, ฐาน 2)",
        "f_capacity_bytes": "ความจุ (bytes)",
        "f_type": "ชนิดการ์ด",
        "f_device": "อุปกรณ์ (sysfs)",
        "f_cid_hex": "CID (hex)",
        "f_note": "หมายเหตุ",
    },
}

LANG_NAMES = {"en": "English", "th": "ไทย"}


def default_language():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            lang = json.load(f).get("lang")
            if lang in STR:
                return lang
    except (OSError, ValueError):
        pass
    try:
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:  # noqa
        loc = ""
    return "th" if loc.lower().startswith("th") else "en"


# --------------------------------------------------------------------------
# Decoding
# --------------------------------------------------------------------------
class HexError(ValueError):
    def __init__(self, name, n):
        super().__init__("%s: %d" % (name, n))
        self.name, self.n = name, n


def crc7(data: bytes) -> int:
    crc = 0
    for byte in data:
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            top = (crc >> 6) & 1
            crc = (crc << 1) & 0x7F
            if top ^ bit:
                crc ^= 0x09
    return crc


def ascii_clean(b: bytes) -> str:
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in b)


def clean_hex32(s: str, name: str) -> str:
    s = re.sub(r"[^0-9a-fA-F]", "", s)
    if len(s) != 32:
        raise HexError(name, len(s))
    return s


def decode_cid(hexstr: str) -> dict:
    hexstr = clean_hex32(hexstr, "CID")
    raw = bytes.fromhex(hexstr)
    mid = raw[0]
    psn = int.from_bytes(raw[9:13], "big")
    mdt = ((raw[13] & 0x0F) << 8) | raw[14]
    stored, calc = raw[15] >> 1, crc7(raw[:15])
    return {
        "manufacturer_name": MANUFACTURERS.get(mid),   # None = unknown
        "manufacturer_id": "0x%02X" % mid,
        "oem_application_id": ascii_clean(raw[1:3]),
        "product_name": ascii_clean(raw[3:8]),
        "product_revision": "%d.%d" % (raw[8] >> 4, raw[8] & 0x0F),
        "serial_number_hex": "0x%08X" % psn,
        "serial_number_dec": psn,
        "manufacture_date": "%04d-%02d" % (2000 + (mdt >> 4), mdt & 0x0F),
        "crc7_stored": "0x%02X" % stored,
        "crc7_calculated": "0x%02X" % calc,
        "crc_ok": stored == calc,
        "cid_hex": hexstr.lower(),
    }


def decode_csd(hexstr: str) -> dict:
    v = int(clean_hex32(hexstr, "CSD"), 16)
    s = (v >> 126) & 3
    if s == 0:      # CSD v1.0 (SDSC)
        cap = (((v >> 62) & 0xFFF) + 1) * (1 << (((v >> 47) & 7) + 2)) * (1 << ((v >> 80) & 0xF))
        ver = "1.0 (SDSC)"
    elif s == 1:    # CSD v2.0 (SDHC / SDXC)
        cap = (((v >> 48) & 0x3FFFFF) + 1) * 512 * 1024
        ver = "2.0 (SDHC/SDXC)"
    elif s == 2:    # CSD v3.0 (SDUC)
        cap = (((v >> 48) & 0xFFFFFFF) + 1) * 512 * 1024
        ver = "3.0 (SDUC)"
    else:
        return {"csd_version": "?"}
    return {
        "csd_version": ver,
        "capacity_gb": round(cap / 1e9, 2),
        "capacity_gib": round(cap / 2 ** 30, 2),
        "capacity_bytes": cap,
    }


# --------------------------------------------------------------------------
# Reading from this computer
# --------------------------------------------------------------------------
def read_linux():
    items = []
    for dev in sorted(glob.glob("/sys/class/mmc_host/mmc*/mmc*:*")):
        def rd(name, dev=dev):
            try:
                with open(os.path.join(dev, name)) as f:
                    return f.read().strip()
            except OSError:
                return None
        cid = rd("cid")
        if not cid:
            continue
        info = decode_cid(cid)
        info["device"] = dev
        info["type"] = rd("type")
        csd = rd("csd")
        if csd:
            info.update(decode_csd(csd))
        for key in ("fwrev", "hwrev", "ocr", "scr", "ssr", "erase_size"):
            val = rd(key)
            if val:
                info["sysfs_" + key] = val
        items.append(info)
    return items


def read_macos():
    try:
        out = subprocess.run(["system_profiler", "SPCardReaderDataType"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa
        return []
    return [{"note_key": "note_os_macos", "raw": out}] if out else []


def read_windows():
    ps = ("Get-PhysicalDisk | Select-Object FriendlyName,SerialNumber,Size,BusType,"
          "MediaType | ConvertTo-Json")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30,
                             creationflags=flags).stdout
        data = json.loads(out) if out.strip() else []
        if isinstance(data, dict):
            data = [data]
        return [{"note_key": "note_os_windows", **d} for d in data]
    except Exception:  # noqa
        return []


def auto_read():
    system = platform.system()
    if system == "Linux":
        return read_linux()
    if system == "Darwin":
        return read_macos()
    if system == "Windows":
        return read_windows()
    return []


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = default_language()
        self.geometry("780x760")
        self.minsize(660, 600)
        self.items = []
        self.current = None
        self._i18n = []          # (widget, option, key)
        self._status = ("status_ready", {})

        pad = {"padx": 10, "pady": 4}

        # ---- language bar
        bar0 = ttk.Frame(self)
        bar0.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(bar0, text="Language / ภาษา").pack(side="right", padx=(6, 0))
        self.lang_var = tk.StringVar(value=LANG_NAMES[self.lang])
        self.lang_combo = ttk.Combobox(bar0, textvariable=self.lang_var, state="readonly",
                                       width=9, values=list(LANG_NAMES.values()))
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_language)

        # ---- read from this computer
        top = ttk.LabelFrame(self)
        top.pack(fill="x", **pad)
        self.reg(top, "grp_auto")
        self.btn_auto = ttk.Button(top, command=self.on_auto)
        self.reg(self.btn_auto, "btn_auto")
        self.btn_auto.pack(side="left", padx=8, pady=8)
        self.card_var = tk.StringVar()
        self.card_combo = ttk.Combobox(top, textvariable=self.card_var, state="readonly", width=48)
        self.card_combo.pack(side="left", padx=8, fill="x", expand=True)
        self.card_combo.bind("<<ComboboxSelected>>", self.on_select_card)

        # ---- manual hex
        manual = ttk.LabelFrame(self)
        manual.pack(fill="x", **pad)
        self.reg(manual, "grp_manual")
        manual.columnconfigure(1, weight=1)
        l1 = ttk.Label(manual)
        self.reg(l1, "lbl_cid")
        l1.grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.cid_entry = ttk.Entry(manual, font=("Courier", 10))
        self.cid_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        l2 = ttk.Label(manual)
        self.reg(l2, "lbl_csd")
        l2.grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.csd_entry = ttk.Entry(manual, font=("Courier", 10))
        self.csd_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        b = ttk.Button(manual, command=self.on_decode)
        self.reg(b, "btn_decode")
        b.grid(row=0, column=2, rowspan=2, padx=8, pady=4, sticky="ns")
        hint = ttk.Label(manual, foreground="gray")
        self.reg(hint, "hint_csd")
        hint.grid(row=2, column=1, sticky="w", padx=8, pady=(0, 6))

        # ---- RP2040 / Pico serial
        pico = ttk.LabelFrame(self)
        pico.pack(fill="x", **pad)
        self.reg(pico, "grp_pico")
        lp = ttk.Label(pico)
        self.reg(lp, "lbl_port")
        lp.pack(side="left", padx=(8, 4), pady=8)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(pico, textvariable=self.port_var, state="normal", width=40)
        self.port_combo.pack(side="left", padx=4, fill="x", expand=True)
        rb = ttk.Button(pico, command=self.refresh_ports)
        self.reg(rb, "btn_refresh")
        rb.pack(side="left", padx=4)
        self.btn_pico = ttk.Button(pico, command=self.on_pico)
        self.reg(self.btn_pico, "btn_pico")
        self.btn_pico.pack(side="left", padx=8)
        self.refresh_ports()

        # ---- results
        res = ttk.LabelFrame(self)
        res.pack(fill="both", expand=True, **pad)
        self.reg(res, "grp_result")
        self.tree = ttk.Treeview(res, columns=("field", "value"), show="headings", height=12)
        self.tree.column("field", width=240, anchor="w")
        self.tree.column("value", width=450, anchor="w")
        sb = ttk.Scrollbar(res, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", pady=8, padx=(0, 8))
        self.tree.tag_configure("bad", foreground="#c0392b")
        self.tree.tag_configure("good", foreground="#1e8449")

        # ---- bottom buttons
        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        for key, cmd in (("btn_copy", self.on_copy), ("btn_save", self.on_save),
                         ("btn_clear", self.on_clear)):
            w = ttk.Button(bar, command=cmd)
            self.reg(w, key)
            w.pack(side="left", padx=(0, 8))

        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w").pack(
            fill="x", side="bottom")

        self.apply_language()

    # ---------- i18n helpers
    def t(self, key, **kw):
        s = STR[self.lang].get(key) or STR["en"].get(key, key)
        return s.format(**kw) if kw else s

    def reg(self, widget, key, option="text"):
        self._i18n.append((widget, option, key))

    def set_status(self, key, **kw):
        self._status = (key, kw)
        self.status.set(self.t(key, **kw))

    def apply_language(self):
        self.title(self.t("title"))
        for widget, option, key in self._i18n:
            widget.configure(**{option: self.t(key)})
        self.tree.heading("field", text=self.t("col_field"))
        self.tree.heading("value", text=self.t("col_value"))
        self._fill_card_combo()
        if self.current:
            self.show(self.current)
        self.refresh_ports(keep_selection=True)
        self.set_status(self._status[0], **self._status[1])

    def on_language(self, _=None):
        chosen = self.lang_var.get()
        for code, name in LANG_NAMES.items():
            if name == chosen:
                self.lang = code
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"lang": self.lang}, f)
        except OSError:
            pass
        self.apply_language()

    # ---------- results table
    def _rows(self, info):
        rows = []
        keys = [k for k in FIELD_ORDER if k in info] + [k for k in info if k not in FIELD_ORDER]
        for k in keys:
            v = info[k]
            if k == "raw":
                rows += [("", line, ()) for line in str(v).splitlines()]
                continue
            if k == "note_key":
                rows.append((self.t("f_note"), self.t(v), ()))
                continue
            tag = ()
            if k == "manufacturer_name" and v is None:
                v = self.t("unknown_mfr")
            if k == "crc_ok":
                tag = ("good",) if v else ("bad",)
                v = self.t("crc_yes") if v else self.t("crc_no")
            label = STR[self.lang].get("f_" + k) or STR["en"].get("f_" + k, k)
            rows.append((label, str(v), tag))
        return rows

    def show(self, info):
        self.current = info
        self.tree.delete(*self.tree.get_children())
        for label, value, tag in self._rows(info):
            self.tree.insert("", "end", values=(label, value), tags=tag)

    # ---------- auto-read (in a thread so the UI never freezes)
    def on_auto(self):
        self.btn_auto.state(["disabled"])
        self.set_status("status_reading")
        threading.Thread(target=self._auto_worker, daemon=True).start()

    def _auto_worker(self):
        try:
            items, err = auto_read(), None
        except Exception as e:  # noqa
            items, err = [], str(e)
        self.after(0, self._auto_done, items, err)

    def _card_names(self):
        names = []
        for n, it in enumerate(self.items, 1):
            if "cid_hex" in it:
                mfr = it["manufacturer_name"] or self.t("unknown_mfr")
                names.append("%d) %s %s  [S/N %s]" % (
                    n, mfr, it["product_name"], it["serial_number_hex"]))
            else:
                names.append("%d) %s" % (n, it.get("FriendlyName", self.t("generic_info"))))
        return names

    def _fill_card_combo(self):
        if not self.items:
            self.card_combo["values"] = []
            return
        idx = self.card_combo.current()
        self.card_combo["values"] = self._card_names()
        if idx >= 0:
            self.card_combo.current(idx)

    def _auto_done(self, items, err):
        self.btn_auto.state(["!disabled"])
        self.items = items
        if err:
            self.set_status("status_error")
            messagebox.showerror(self.t("dlg_error"), err)
            return
        if not items:
            self.card_combo["values"] = []
            self.card_var.set("")
            self.set_status("status_nocard")
            messagebox.showinfo(self.t("dlg_nodata_title"), self.t("dlg_nodata_msg"))
            return
        self._fill_card_combo()
        self.card_combo.current(0)
        self.show(items[0])
        if any("cid_hex" in i for i in items):
            self.set_status("status_cards", n=len(items))
        else:
            self.set_status("status_os_only")

    def on_select_card(self, _):
        i = self.card_combo.current()
        if 0 <= i < len(self.items):
            self.show(self.items[i])

    # ---------- decode typed hex
    def on_decode(self):
        try:
            info = decode_cid(self.cid_entry.get())
            if self.csd_entry.get().strip():
                info.update(decode_csd(self.csd_entry.get()))
        except HexError as e:
            messagebox.showerror(self.t("dlg_invalid"),
                                 self.t("hex_len_error", name=e.name, n=e.n))
            return
        self.items = [info]
        self.card_combo["values"] = []
        self.card_var.set("")
        self.show(info)
        self.set_status("status_decoded")

    # ---------- RP2040 / Pico over USB serial
    def refresh_ports(self, keep_selection=False):
        if serial is None:
            self.port_combo["values"] = [self.t("pyserial_missing")]
            self.port_combo.current(0)
            return
        ports = sorted(list_ports.comports(), key=lambda p: 0 if p.vid == 0x2E8A else 1)
        values = ["%s - %s" % (p.device, p.description) for p in ports]
        self.port_combo["values"] = values
        if keep_selection and self.port_var.get():
            return
        if values:
            self.port_combo.current(0)
        else:
            self.port_var.set("")

    def on_pico(self):
        if serial is None:
            messagebox.showinfo(self.t("dlg_need_pyserial_title"),
                                self.t("dlg_need_pyserial_msg"))
            return
        sel = self.port_var.get().strip()
        if not sel or sel.startswith("("):
            messagebox.showinfo(self.t("dlg_noport_title"), self.t("dlg_noport_msg"))
            return
        self.btn_pico.state(["disabled"])
        self.set_status("status_pico_reading")
        threading.Thread(target=self._pico_worker, args=(sel.split(" - ")[0].strip(),),
                         daemon=True).start()

    def _pico_worker(self, port):
        cid = csd = err = None
        try:
            with serial.Serial(port, 115200, timeout=0.5) as s:
                s.reset_input_buffer()
                s.write(b"r\n")
                deadline = time.time() + 8
                while time.time() < deadline:
                    line = s.readline().decode(errors="ignore").strip()
                    if line.startswith("CID="):
                        cid = line[4:]
                    elif line.startswith("CSD="):
                        csd = line[4:]
                    elif line.startswith("ERR="):
                        err = line[4:]
                        break
                    if cid and csd:
                        break
                if not cid and not err:
                    err = "NO_REPLY"
        except Exception as e:  # noqa
            err = str(e)
        self.after(0, self._pico_done, cid, csd, err)

    def _pico_done(self, cid, csd, err):
        self.btn_pico.state(["!disabled"])
        if not cid:
            self.set_status("status_pico_fail")
            key = "err_" + (err or "unknown").lower()
            msg = self.t(key) if key in STR["en"] else (err or self.t("err_unknown"))
            messagebox.showerror(self.t("dlg_pico_fail"), msg)
            return
        self.cid_entry.delete(0, "end")
        self.cid_entry.insert(0, cid)
        self.csd_entry.delete(0, "end")
        if csd:
            self.csd_entry.insert(0, csd)
        self.on_decode()
        self.set_status("status_pico_ok")

    # ---------- tools
    def on_copy(self):
        if not self.current:
            return
        text = "\n".join("%s: %s" % (l, v) if l else v for l, v, _ in self._rows(self.current))
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("status_copied")

    def on_save(self):
        if not self.current:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile="sdcard_cid.json")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.current, f, indent=2, ensure_ascii=False)
            self.set_status("status_saved", path=path)

    def on_clear(self):
        self.tree.delete(*self.tree.get_children())
        self.cid_entry.delete(0, "end")
        self.csd_entry.delete(0, "end")
        self.card_combo["values"] = []
        self.card_var.set("")
        self.items, self.current = [], None
        self.set_status("status_ready")


def main():
    if platform.system() == "Windows":
        try:  # sharper text on high-DPI displays
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
