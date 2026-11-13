"""The stock firmware: which file it is, how to check it, how to download it.

The download asks the maker's update catalog for the address of the file, with
the request that the maker's own updater program sends. The camera model code
is real; the network address and the serial number are placeholders. Nothing
about the user or the user's camera is sent.
"""

from __future__ import annotations

import datetime
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .errors import StockError
from .hashing import sha256_file
from .paths import RepoPaths

CATALOG_URL = "https://fw01.om-digitalsolutions.net/ww_inform/fcache.do"
USER_AGENT = "Olympus"
_TIMEOUT_SECONDS = 120
_BLOCK_SIZE = 1 << 20


@dataclass(frozen=True)
class StockFirmware:
    """The identity of one stock firmware file.

    Attributes:
        file_name: the maker's name of the file.
        relative_path: where the file is kept, relative to the repository root.
        size: size in bytes.
        sha256: SHA-256 of the file.
        model_id: the model number in the update catalog.
        hard_code: the model code that the updater sends to the catalog.
        card_name: the name the camera's updater looks for on the SD card.
    """

    file_name: str
    relative_path: str
    size: int
    sha256: str
    model_id: str
    hard_code: str
    card_name: str


#: Olympus PEN E-PM2, body firmware 1.6. Every build starts from this file.
EPM2_V16 = StockFirmware(
    file_name="OLY_E_101_1600_0000_0000.BIN",
    relative_path="firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
    size=43319360,
    sha256="34d339ac3986ba8c10f494dbe2e4ae8f143ebf5bbfaa356e3ff9b7f40fc3e300",
    model_id="1010",
    hard_code="OLYE101000000000",
    card_name="E1019999.BIN",
)

#: Folder on the SD card that the camera's updater reads.
CARD_FOLDER = "DCOLYMP"

_REQUEST = (
    "<?xml version='1.0' encoding='utf-8'?><firmware_demand><revision>0001</revision>"
    "<mac_address>00-00-00-00-00-00</mac_address><time>{time}</time>"
    "<language>ENU</language><application>FWUT</application><type>0000</type>"
    "<version>00005000</version><os>WIN</os><country_code>0001</country_code>"
    "<hardwares><firmup_mode>0</firmup_mode><hardware_info>"
    "<hard_code>{hard_code}</hard_code><firmware_version>00001000</firmware_version>"
    "<serial_no>000000000</serial_no></hardware_info></hardwares></firmware_demand>"
)

Log = Callable[[str], None]


def stock_path(paths: RepoPaths, stock: StockFirmware = EPM2_V16) -> Path:
    """Return where the stock firmware file is kept."""
    return paths.resolve(stock.relative_path)


def is_stock(path: Path, stock: StockFirmware = EPM2_V16) -> bool:
    """Return True if ``path`` is a file with the stock firmware's SHA-256."""
    return path.is_file() and sha256_file(path) == stock.sha256


def catalog_request(stock: StockFirmware, now: datetime.datetime) -> bytes:
    """Return the body of the catalog request for a firmware, at time ``now``."""
    return _REQUEST.format(
        time=now.strftime("%Y%m%d%H%M%S"), hard_code=stock.hard_code
    ).encode("utf-8")


def download_url(answer: bytes, stock: StockFirmware) -> str:
    """Read the download address from the catalog's answer.

    Raises:
        StockError: if the answer is not XML, or does not offer this firmware
            from an HTTPS address.
    """
    try:
        info = ElementTree.fromstring(answer).find(".//firmware_info")
    except ElementTree.ParseError as error:
        raise StockError(f"the catalog's answer is not XML: {error}") from None
    offered = info.findtext("file_name") if info is not None else None
    if (
        info is None
        or info.findtext("model_id") != stock.model_id
        or offered != stock.file_name
    ):
        raise StockError(
            f"the catalog does not offer {stock.file_name} "
            f"(it offers {offered or 'nothing'})"
        )
    url = info.findtext("url") or ""
    if not url.startswith("https://"):
        raise StockError(f"the catalog gave an address that is not HTTPS: {url!r}")
    return url


def _open(request: urllib.request.Request) -> "urllib.request._UrlopenRet":
    """Open a request; network errors become ``StockError``."""
    try:
        return urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS)  # noqa: S310
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise StockError(f"download failed: {error}") from None


def fetch(
    paths: RepoPaths,
    stock: StockFirmware = EPM2_V16,
    log: Optional[Log] = None,
) -> Path:
    """Make sure the stock firmware file is in the repository, and return its path.

    If the file is there and has the right SHA-256, nothing is downloaded. If a
    different file is there, it is left alone and an error is raised. The
    download goes to a ``.part`` file that is renamed only after its size and
    SHA-256 are right.

    Args:
        paths: the repository.
        stock: which firmware.
        log: where progress lines go; None for silence.

    Returns:
        The path of the checked file.

    Raises:
        StockError: if another file is in the way, the catalog does not offer
            the firmware, the download fails, or the downloaded file is wrong.
    """
    say = log or (lambda line: None)
    destination = stock_path(paths, stock)
    if destination.exists():
        if is_stock(destination, stock):
            say(f"already there and correct: {paths.relative(destination)}")
            return destination
        raise StockError(
            f"{paths.relative(destination)} exists but is not {stock.file_name} "
            "(the sha256 differs). Move it away and run this again."
        )
    now = datetime.datetime.now(datetime.timezone.utc)
    request = urllib.request.Request(
        CATALOG_URL,
        data=catalog_request(stock, now),
        headers={"User-Agent": USER_AGENT, "Content-Type": "text/xml; Charset=UTF-8"},
    )
    with _open(request) as response:
        url = download_url(response.read(), stock)
    host = url.split("/")[2]
    say(f"downloading {stock.file_name} ({stock.size / 1e6:.0f} MB) from {host}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    try:
        download = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with _open(download) as response, part.open("wb") as handle:
            for block in iter(lambda: response.read(_BLOCK_SIZE), b""):
                handle.write(block)
        size, digest = part.stat().st_size, sha256_file(part)
        if size != stock.size or digest != stock.sha256:
            raise StockError(
                f"the downloaded file is not {stock.file_name} "
                f"(size {size}, sha256 {digest}); nothing was kept"
            )
        part.replace(destination)
    except OSError as error:
        raise StockError(f"download failed: {error}") from None
    finally:
        if part.exists():
            part.unlink()
    say(f"ok: {paths.relative(destination)} sha256 {stock.sha256}")
    return destination
