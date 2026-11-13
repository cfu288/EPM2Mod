"""Patch specs: what they are and how they are applied.

A patch spec is a JSON file::

    {
      "name": "pixel-hacking",
      "description": "...",
      "base": "firmware/stock/E-PM2/OLY_E_101_1600_0000_0000.BIN",
      "base_sha256": "...",
      "ops": [ ... ],
      "expected_sha256": "..."        (optional: the result of this spec alone)
    }

It may hold other keys (``status``, ``attribution``); they are kept as notes
and not interpreted.

There are two kinds of operation. Both keep the size of the firmware, and both
check the bytes that they replace::

    {"type": "bytes", "block": 0, "offset": "0x2CCEC0", "expect": "hex", "new": "hex"}
    {"type": "utf16-replace-all", "block": 1, "old": "text", "new": "text", "count": 16}

``offset`` is a position in the unscrambled payload of the block. It may be a
number or a string in any base that Python's ``int(text, 0)`` reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .container import Container, parse, serialize
from .errors import SpecError
from .hashing import sha256_bytes

UTF16 = "utf-16-le"


@dataclass(frozen=True)
class BytesOp:
    """Replace a run of bytes at a fixed offset.

    Attributes:
        block: index of the container block.
        offset: position in the block's unscrambled payload.
        expect: the bytes that must be there now.
        new: the bytes to write; same length as ``expect``.
    """

    block: int
    offset: int
    expect: bytes
    new: bytes

    def describe(self) -> str:
        """Return a one-line description of the operation."""
        return (
            f"block{self.block}+{self.offset:#x}: "
            f"{self.expect.hex()} -> {self.new.hex()}"
        )


@dataclass(frozen=True)
class Utf16ReplaceAllOp:
    """Replace every aligned UTF-16 copy of a text with another of the same length.

    Attributes:
        block: index of the container block.
        old: the text to find.
        new: the text to write; same number of UTF-16 bytes as ``old``.
        count: how many copies there must be, or None to accept any number.
    """

    block: int
    old: str
    new: str
    count: Optional[int]

    def describe(self) -> str:
        """Return a one-line description of the operation."""
        return f"block{self.block}: '{self.old}' -> '{self.new}'"


Op = Union[BytesOp, Utf16ReplaceAllOp]


@dataclass(frozen=True)
class PatchSpec:
    """A patch spec, read from a file.

    Attributes:
        name: the spec's name.
        description: free text.
        base: path of the stock firmware, relative to the repository root.
        base_sha256: SHA-256 that the stock firmware must have.
        ops: the operations, in order.
        expected_sha256: SHA-256 of the firmware made from this spec alone, if known.
        source: the file the spec was read from, or None.
    """

    name: str
    description: str
    base: str
    base_sha256: str
    ops: Tuple[Op, ...]
    expected_sha256: Optional[str] = None
    source: Optional[Path] = None


def _require(mapping: Mapping[str, Any], key: str, kind: type, where: str) -> Any:
    """Return ``mapping[key]`` after checking that it exists and has the right type."""
    if key not in mapping:
        raise SpecError(f"{where}: missing '{key}'")
    value = mapping[key]
    if not isinstance(value, kind) or isinstance(value, bool):
        raise SpecError(f"{where}: '{key}' must be {kind.__name__}")
    return value


def _hex(mapping: Mapping[str, Any], key: str, where: str) -> bytes:
    """Return the bytes of a hexadecimal string field."""
    text = _require(mapping, key, str, where)
    try:
        return bytes.fromhex(text)
    except ValueError as error:
        raise SpecError(f"{where}: '{key}' is not hexadecimal: {error}") from None


def op_from_json(raw: Mapping[str, Any], where: str) -> Op:
    """Build one operation from its JSON form.

    Args:
        raw: the JSON object of the operation.
        where: text that names the operation in error messages.

    Raises:
        SpecError: if a field is missing or wrong, or the type is not known.
    """
    kind = _require(raw, "type", str, where)
    block = _require(raw, "block", int, where)
    if block < 0:
        raise SpecError(f"{where}: 'block' must not be negative")
    if kind == "bytes":
        if "offset" not in raw:
            raise SpecError(f"{where}: missing 'offset'")
        raw_offset = raw["offset"]
        try:
            offset = (
                int(raw_offset, 0) if isinstance(raw_offset, str) else int(raw_offset)
            )
        except (TypeError, ValueError):
            raise SpecError(
                f"{where}: 'offset' is not a number: {raw_offset!r}"
            ) from None
        if isinstance(raw_offset, bool) or offset < 0:
            raise SpecError(f"{where}: 'offset' must be a number that is not negative")
        expect, new = _hex(raw, "expect", where), _hex(raw, "new", where)
        if len(expect) != len(new):
            raise SpecError(
                f"{where}: 'expect' has {len(expect)} bytes and 'new' has {len(new)}"
            )
        if not new:
            raise SpecError(f"{where}: 'expect' and 'new' are empty")
        return BytesOp(block, offset, expect, new)
    if kind == "utf16-replace-all":
        old, new_text = _require(raw, "old", str, where), _require(
            raw, "new", str, where
        )
        if not old:
            raise SpecError(f"{where}: 'old' is empty")
        if len(old.encode(UTF16)) != len(new_text.encode(UTF16)):
            raise SpecError(f"{where}: '{old}' and '{new_text}' differ in length")
        count = raw.get("count")
        if count is not None and (
            not isinstance(count, int) or isinstance(count, bool) or count < 0
        ):
            raise SpecError(f"{where}: 'count' must be a number that is not negative")
        return Utf16ReplaceAllOp(block, old, new_text, count)
    raise SpecError(f"{where}: unknown operation type '{kind}'")


def spec_from_json(raw: Mapping[str, Any], source: Optional[Path] = None) -> PatchSpec:
    """Build a patch spec from its JSON form.

    Raises:
        SpecError: if the JSON is not a valid spec.
    """
    where = str(source) if source else "spec"
    if not isinstance(raw, Mapping):
        raise SpecError(f"{where}: a spec must be a JSON object")
    name = _require(raw, "name", str, where)
    ops_raw = _require(raw, "ops", list, where)
    ops = tuple(
        op_from_json(_as_mapping(item, f"{name} op {index}"), f"{name} op {index}")
        for index, item in enumerate(ops_raw)
    )
    expected = raw.get("expected_sha256")
    if expected is not None and not isinstance(expected, str):
        raise SpecError(f"{where}: 'expected_sha256' must be str")
    description = raw.get("description", "")
    return PatchSpec(
        name=name,
        description=description if isinstance(description, str) else "",
        base=_require(raw, "base", str, where),
        base_sha256=_require(raw, "base_sha256", str, where),
        ops=ops,
        expected_sha256=expected or None,
        source=source,
    )


def _as_mapping(item: Any, where: str) -> Mapping[str, Any]:
    """Return ``item`` if it is a JSON object, else raise."""
    if not isinstance(item, Mapping):
        raise SpecError(f"{where}: an operation must be a JSON object")
    return item


def load_spec(path: Path) -> PatchSpec:
    """Read a patch spec file.

    Raises:
        SpecError: if the file is missing, is not JSON, or is not a valid spec.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SpecError(f"{path}: cannot be read: {error.strerror}") from None
    except ValueError as error:
        raise SpecError(f"{path}: not JSON: {error}") from None
    return spec_from_json(raw, path)


def apply_op(payloads: List[bytearray], op: Op) -> str:
    """Apply one operation to the payloads, in place.

    Args:
        payloads: the unscrambled payload of every block of the container.
        op: the operation.

    Returns:
        A line of text that says what was done.

    Raises:
        SpecError: if the block does not exist, the bytes to replace are not
            the expected ones, or the count of a text replacement is wrong.
    """
    if op.block >= len(payloads):
        raise SpecError(
            f"{op.describe()}: the firmware has {len(payloads)} blocks, "
            f"there is no block {op.block}"
        )
    payload = payloads[op.block]
    if isinstance(op, BytesOp):
        end = op.offset + len(op.expect)
        if end > len(payload):
            raise SpecError(
                f"block{op.block}+{op.offset:#x}: {len(op.expect)} bytes do not "
                f"fit in a payload of {len(payload)} bytes"
            )
        found = bytes(payload[op.offset : end])
        if found != op.expect:
            raise SpecError(
                f"block{op.block}+{op.offset:#x}: found {found.hex()}, "
                f"expected {op.expect.hex()}"
            )
        payload[op.offset : end] = op.new
        return op.describe()
    old, new = op.old.encode(UTF16), op.new.encode(UTF16)
    hits: List[int] = []
    position = payload.find(old)
    while position >= 0:
        if position % 2 == 0:
            hits.append(position)
        position = payload.find(old, position + 1)
    if op.count is not None and len(hits) != op.count:
        raise SpecError(
            f"'{op.old}': found {len(hits)} aligned copies in block {op.block}, "
            f"the spec expects {op.count}"
        )
    for hit in hits:
        payload[hit : hit + len(new)] = new
    return f"{op.describe()} x{len(hits)}"


@dataclass(frozen=True)
class Applied:
    """The result of applying specs to a firmware image.

    Attributes:
        image: the new firmware file.
        log: one line per operation, with the spec names as headings.
        changed_bytes: how many bytes of the file differ from the stock file.
    """

    image: bytes
    log: Tuple[str, ...]
    changed_bytes: int


def apply_specs(stock: bytes, specs: Sequence[PatchSpec]) -> Applied:
    """Apply patch specs to a stock firmware file, in order.

    Each operation sees the result of the operations before it, so a later spec
    can change bytes that an earlier spec wrote, if its ``expect`` says so.

    Args:
        stock: the stock firmware file.
        specs: the specs, in the order to apply.

    Returns:
        The new firmware file with fresh checksums, and a log.

    Raises:
        SpecError: if there is no spec, a spec is for another base, or an
            operation does not fit.
        ContainerError: if ``stock`` is not a firmware container.
    """
    if not specs:
        raise SpecError("no patch spec given")
    stock_sha = sha256_bytes(stock)
    for spec in specs:
        if spec.base_sha256 != stock_sha:
            raise SpecError(
                f"{spec.name}: is for a base with sha256 {spec.base_sha256}, "
                f"the stock firmware has {stock_sha}"
            )
    container: Container = parse(stock)
    payloads = [bytearray(block.payload) for block in container.blocks]
    log: List[str] = []
    for spec in specs:
        log.append(f"[{spec.name}]")
        for index, op in enumerate(spec.ops):
            try:
                log.append("  " + apply_op(payloads, op))
            except SpecError as error:
                raise SpecError(f"{spec.name} op {index}: {error}") from None
    image = serialize(container.with_payloads([bytes(p) for p in payloads]))
    changed = sum(a != b for a, b in zip(stock, image))
    return Applied(image, tuple(log), changed)


def op_to_json(op: Op) -> Dict[str, Any]:
    """Return the JSON form of an operation."""
    if isinstance(op, BytesOp):
        return {
            "type": "bytes",
            "block": op.block,
            "offset": hex(op.offset),
            "expect": op.expect.hex(),
            "new": op.new.hex(),
        }
    raw: Dict[str, Any] = {
        "type": "utf16-replace-all",
        "block": op.block,
        "old": op.old,
        "new": op.new,
    }
    if op.count is not None:
        raw["count"] = op.count
    return raw
