#!/usr/bin/env python3
"""Download the stock Olympus E-PM2 v1.6 firmware from the maker's update catalog and check it.

    python3 tools/fetch_stock.py          -> firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN

It sends the request that the maker's own updater program sends (camera model code, a placeholder
serial number and network address), reads the download address from the answer, downloads the file
and compares its sha256 with the one this project is built on. It never talks to a camera.
Python standard library only.
"""
import datetime, hashlib, os, sys, urllib.request, xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = "https://fw01.om-digitalsolutions.net/ww_inform/fcache.do"
NAME, SIZE, MODEL_ID = "OLY_E_101_1600_0000_0000.BIN", 43319360, "1010"
SHA256 = "34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300"
DEST = os.path.join(ROOT, "firmware", "stock", "E-PM2", NAME)
REQUEST = ("<?xml version='1.0' encoding='utf-8'?><firmware_demand><revision>0001</revision><mac_address>00-00-00-00-00-00</mac_address>"
           "<time>{time}</time><language>ENU</language><application>FWUT</application><type>0000</type><version>00005000</version><os>WIN</os>"
           "<country_code>0001</country_code><hardwares><firmup_mode>0</firmup_mode><hardware_info><hard_code>OLYE101000000000</hard_code>"
           "<firmware_version>00001000</firmware_version><serial_no>000000000</serial_no></hardware_info></hardwares></firmware_demand>")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if os.path.exists(DEST):
        if sha256_of(DEST) == SHA256:
            print(f"already there and correct: {DEST}")
            return 0
        sys.exit(f"{DEST} exists but is not stock E-PM2 v1.6 (sha256 differs). Move it away and run this again.")
    body = REQUEST.format(time=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")).encode()
    req = urllib.request.Request(CATALOG, data=body, headers={"User-Agent": "Olympus", "Content-Type": "text/xml; Charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        info = ET.fromstring(r.read()).find(".//firmware_info")
    if info is None or info.findtext("model_id") != MODEL_ID or info.findtext("file_name") != NAME:
        sys.exit("The catalog did not offer E-PM2 firmware 1.6 (" + (info.findtext("file_name") if info is not None else "no entry")
                 + "). Get the file another way (firmware/README.md) and put it at " + DEST)
    url = info.findtext("url")
    print(f"downloading {NAME} ({SIZE / 1e6:.0f} MB) from {url.split('/')[2]}")
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    part = DEST + ".part"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Olympus"}), timeout=120) as r, open(part, "wb") as f:
        for block in iter(lambda: r.read(1 << 20), b""):
            f.write(block)
    got = sha256_of(part)
    if os.path.getsize(part) != SIZE or got != SHA256:
        os.remove(part)
        sys.exit(f"the downloaded file is not the expected one (sha256 {got}); nothing was kept")
    os.replace(part, DEST)
    print(f"ok: {DEST}\nsha256 {SHA256}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
