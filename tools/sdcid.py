#!/usr/bin/env python3
"""
sdcid.py - command-line SD / microSD CID + CSD decoder (English output)

Usage:
  python3 sdcid.py                         # Linux: read the card from sysfs
  python3 sdcid.py --cid <32 hex>          # decode a CID you already have
  python3 sdcid.py --cid <hex> --csd <hex> # also compute the capacity
  python3 sdcid.py --json
"""
import argparse
import glob
import json
import os
import platform
import re
import sys

MANUFACTURERS = {
    0x01: "Panasonic", 0x02: "Toshiba / Kioxia", 0x03: "SanDisk (Western Digital)",
    0x06: "Ritek", 0x09: "ATP Electronics", 0x12: "Patriot Memory", 0x13: "Kingmax",
    0x15: "Samsung (eMMC)", 0x1B: "Samsung", 0x1D: "ADATA", 0x1F: "Kingston (Phison OEM)",
    0x27: "Phison", 0x28: "Lexar (Longsys)", 0x31: "Silicon Power", 0x41: "Kingston",
    0x6F: "STMicroelectronics", 0x74: "Transcend", 0x76: "Patriot Memory",
    0x82: "Sony / Gigastone / Jiaelec", 0x9C: "Angelbird / Hoodman / Sony",
}


def crc7(data):
    crc = 0
    for byte in data:
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            top = (crc >> 6) & 1
            crc = (crc << 1) & 0x7F
            if top ^ bit:
                crc ^= 0x09
    return crc


def clean(s, name):
    s = re.sub(r"[^0-9a-fA-F]", "", s)
    if len(s) != 32:
        raise ValueError("%s must be 32 hex characters, got %d" % (name, len(s)))
    return s


def ascii_clean(b):
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in b)


def decode_cid(hexstr):
    hexstr = clean(hexstr, "CID")
    raw = bytes.fromhex(hexstr)
    psn = int.from_bytes(raw[9:13], "big")
    mdt = ((raw[13] & 0x0F) << 8) | raw[14]
    return {
        "cid_hex": hexstr.lower(),
        "manufacturer_id": "0x%02X" % raw[0],
        "manufacturer_name": MANUFACTURERS.get(raw[0], "unknown"),
        "oem_application_id": ascii_clean(raw[1:3]),
        "product_name": ascii_clean(raw[3:8]),
        "product_revision": "%d.%d" % (raw[8] >> 4, raw[8] & 0xF),
        "serial_number_hex": "0x%08X" % psn,
        "serial_number_dec": psn,
        "manufacture_date": "%04d-%02d" % (2000 + (mdt >> 4), mdt & 0xF),
        "crc7_stored": "0x%02X" % (raw[15] >> 1),
        "crc7_calculated": "0x%02X" % crc7(raw[:15]),
        "crc_ok": (raw[15] >> 1) == crc7(raw[:15]),
    }


def decode_csd(hexstr):
    v = int(clean(hexstr, "CSD"), 16)
    s = (v >> 126) & 3
    if s == 0:
        cap = (((v >> 62) & 0xFFF) + 1) * (1 << (((v >> 47) & 7) + 2)) * (1 << ((v >> 80) & 0xF))
        ver = "1.0 (SDSC)"
    elif s == 1:
        cap, ver = (((v >> 48) & 0x3FFFFF) + 1) * 512 * 1024, "2.0 (SDHC/SDXC)"
    elif s == 2:
        cap, ver = (((v >> 48) & 0xFFFFFFF) + 1) * 512 * 1024, "3.0 (SDUC)"
    else:
        return {"csd_version": "unknown"}
    return {"csd_version": ver, "capacity_bytes": cap,
            "capacity_gb": round(cap / 1e9, 2), "capacity_gib": round(cap / 2**30, 2)}


def read_linux():
    out = []
    for dev in sorted(glob.glob("/sys/class/mmc_host/mmc*/mmc*:*")):
        def rd(n, dev=dev):
            try:
                return open(os.path.join(dev, n)).read().strip()
            except OSError:
                return None
        cid = rd("cid")
        if cid:
            info = decode_cid(cid)
            info["device"] = dev
            if rd("csd"):
                info.update(decode_csd(rd("csd")))
            out.append(info)
    return out


def main():
    ap = argparse.ArgumentParser(description="Decode SD card CID/CSD registers")
    ap.add_argument("--cid", help="CID as 32 hex characters")
    ap.add_argument("--csd", help="CSD as 32 hex characters (optional)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.cid:
        info = decode_cid(a.cid)
        if a.csd:
            info.update(decode_csd(a.csd))
        items = [info]
    elif platform.system() == "Linux":
        items = read_linux()
    else:
        items = []
    if not items:
        print("Could not read a CID from this computer. A USB card reader does not expose it.\n"
              "Use the RP2040 board (see README) or pass the value with --cid.", file=sys.stderr)
        sys.exit(1)

    if a.json:
        print(json.dumps(items, indent=2))
    else:
        for it in items:
            print("=" * 50)
            for k, v in it.items():
                print("%-22s : %s" % (k, v))


if __name__ == "__main__":
    main()
