"""The stock firmware: which file it is, how to check it, how to download it.

The download asks the maker's update catalog for the address of the file, with
the request that the maker's own updater program sends. The camera model code
is real; the network address and the serial number are placeholders. Nothing
about the user or the user's camera is sent.

A downloaded file is kept only if its size and SHA-256 are the expected ones,
so the address it came from does not have to be trusted.
"""

from __future__ import annotations

import datetime
import http.client
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import DownloadError, StockError, StockMissingError
from .fileio import Log, read_bytes, silent, write_bytes
from .hashing import sha256_bytes

if TYPE_CHECKING:
    from .catalogue import Locator

CATALOG_URL = "https://fw01.om-digitalsolutions.net/ww_inform/fcache.do"
USER_AGENT = "Olympus"
_TIMEOUT_SECONDS = 120
#: How many bytes of an answer are read at a time.
_READ_SIZE = 1 << 20
_CATALOG_LIMIT = 1 << 20


@dataclass(frozen=True)
class StockFirmware:
    """The identity of one stock firmware file.

    Attributes:
        file_name: the maker's name of the file.
        relative_path: where a checkout keeps the file, relative to its root.
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


def stock_path(paths: Locator, stock: StockFirmware = EPM2_V16) -> Path:
    """Return where the stock firmware file is kept (the locator decides)."""
    return paths.stock_file(stock)


def read_stock(paths: Locator, stock: StockFirmware = EPM2_V16) -> bytes:
    """Return the bytes of the stock firmware file, after checking their SHA-256.

    The check is made on the bytes that are returned, so the caller works on
    exactly what was verified.

    Raises:
        StockError: if the file is missing, cannot be read, or is another file.
    """
    path = stock_path(paths, stock)
    if not path.exists():
        raise StockMissingError(
            f"{paths.relative(path)} is missing: run 'epm2mod fetch-stock'"
        )
    data = read_bytes(path, StockError)
    if sha256_bytes(data) != stock.sha256:
        raise StockError(
            f"{paths.relative(path)} is not {stock.file_name} (the sha256 differs). "
            "Move it away and run 'epm2mod fetch-stock'."
        )
    return data


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
    except (ElementTree.ParseError, LookupError, ValueError) as error:
        raise StockError(f"the catalog's answer is not XML: {error}") from None
    offered = info.findtext("file_name") if info is not None else None
    if (
        info is None
        or info.findtext("model_id") != stock.model_id
        or offered != stock.file_name
    ):
        raise StockError(
            f"the catalog does not offer {stock.file_name} for model "
            f"{stock.model_id} (it offers {offered or 'nothing'})"
        )
    url = info.findtext("url") or ""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        parts = None
    if parts is None or parts.scheme != "https" or not parts.hostname:
        raise StockError(f"the catalog gave an address that is not HTTPS: {url!r}")
    return url


def http_get(request: urllib.request.Request, limit: int) -> bytes:
    """Return the body of the answer to an HTTP request.

    Args:
        request: the request.
        limit: the largest body that is accepted, in bytes.

    Raises:
        StockError: if the request fails, the answer is cut short, or the body
            is larger than ``limit``.
    """
    body = bytearray()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            for block in iter(lambda: response.read(_READ_SIZE), b""):
                body += block
                if len(body) > limit:
                    raise DownloadError(
                        f"{request.full_url}: the answer is larger than {limit} bytes"
                    )
    except (OSError, ValueError, http.client.HTTPException) as error:
        raise DownloadError(f"{request.full_url}: download failed: {error}") from None
    return bytes(body)


def fetch(
    paths: Locator,
    stock: StockFirmware = EPM2_V16,
    log: Log = silent,
) -> Path:
    """Make sure the stock firmware file is in the locator's cache, and return its path.

    If the file is there and has the right SHA-256, nothing is downloaded. If a
    different file is there, it is left alone and an error is raised. A
    downloaded file is written only after its size and SHA-256 are right.

    Args:
        paths: the locator, which says where the file is kept.
        stock: which firmware.
        log: where progress lines go.

    Returns:
        The path of the checked file.

    Raises:
        StockError: if another file is in the way, the catalog does not offer
            the firmware, the download fails, or the downloaded file is wrong.
    """
    destination = stock_path(paths, stock)
    if destination.exists():
        read_stock(paths, stock)
        log(f"already there and correct: {paths.relative(destination)}")
        return destination
    headers = {"User-Agent": USER_AGENT, "Content-Type": "text/xml; Charset=UTF-8"}
    now = datetime.datetime.now(datetime.timezone.utc)
    catalog = urllib.request.Request(
        CATALOG_URL, data=catalog_request(stock, now), headers=headers
    )
    url = download_url(http_get(catalog, _CATALOG_LIMIT), stock)
    host = urllib.parse.urlsplit(url).hostname
    log(f"downloading {stock.file_name} ({stock.size / 1e6:.0f} MB) from {host}")
    download = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    data = http_get(download, stock.size)
    digest = sha256_bytes(data)
    if len(data) != stock.size or digest != stock.sha256:
        raise StockError(
            f"the downloaded file is not {stock.file_name} "
            f"(size {len(data)}, sha256 {digest}); nothing was kept"
        )
    write_bytes(destination, data, StockError)
    log(f"ok: {paths.relative(destination)} sha256 {stock.sha256}")
    return destination


def obtain_stock(
    paths: Locator,
    stock: StockFirmware = EPM2_V16,
    log: Log = silent,
) -> bytes:
    """Return the checked bytes of the stock firmware; download the file if it is absent.

    Raises:
        StockError: as ``fetch`` and ``read_stock``.
    """
    if not stock_path(paths, stock).exists():
        log("the stock firmware is not here: downloading it")
        fetch(paths, stock, log)
    return read_stock(paths, stock)
