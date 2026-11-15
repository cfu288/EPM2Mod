"""Download stock body firmware from the maker's update catalog into a scratch folder.

    python3 fetch_fw.py OUTDIR CODE [CODE ...]      (CODE: E100, E112, ... or a 16-char hard code)

The request is the one tools/fetch_stock.py sends (model code only; no user data).
An answer that is LZMA-packed (.lzma) is unpacked. Prints file name, size, sha256.
Never write the output into the repository.
"""
import datetime, hashlib, lzma, sys, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

URL = "https://fw01.om-digitalsolutions.net/ww_inform/fcache.do"
REQ = ("<?xml version='1.0' encoding='utf-8'?><firmware_demand><revision>0001</revision>"
       "<mac_address>00-00-00-00-00-00</mac_address><time>{time}</time>"
       "<language>ENU</language><application>FWUT</application><type>0000</type>"
       "<version>00005000</version><os>WIN</os><country_code>0001</country_code>"
       "<hardwares><firmup_mode>0</firmup_mode><hardware_info>"
       "<hard_code>{hard}</hard_code><firmware_version>00001000</firmware_version>"
       "<serial_no>000000000</serial_no></hardware_info></hardwares></firmware_demand>")
HEAD = {"User-Agent": "Olympus", "Content-Type": "text/xml; Charset=UTF-8"}


def main() -> None:
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for code in sys.argv[2:]:
        hard = code if len(code) == 16 else f"OLY{code}000000000"
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        req = urllib.request.Request(URL, data=REQ.format(time=now, hard=hard).encode(), headers=HEAD)
        ans = urllib.request.urlopen(req, timeout=120).read()
        (out / f"{code}.reply.xml").write_bytes(ans)
        info = ET.fromstring(ans).find(".//firmware_info")
        if info is None or not info.findtext("url"):
            print(code, "NOT SERVED"); continue
        name, url = info.findtext("file_name"), info.findtext("url")
        dest = out / name
        if not dest.exists():
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Olympus"}), timeout=600).read()
            if url.endswith(".lzma") or data[:3] == b"\x5d\x00\x00":
                data = lzma.decompress(data)
            dest.write_bytes(data)
        data = dest.read_bytes()
        print(code, name, info.findtext("model_name") or "", len(data), hashlib.sha256(data).hexdigest())


main()
