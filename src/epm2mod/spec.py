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

Other keys (``status``, ``attribution``) are notes for people. They are not
read here.

There are two kinds of operation. Both keep the size of the firmware, and both
refuse to write unless they find what they expect::

    {"type": "bytes", "block": 0, "offset": "0x2CCEC0", "expect": "hex", "new": "hex"}
    {"type": "utf16-replace-all", "block": 1, "old": "text", "new": "text", "count": 16}

``offset`` is a position in the unscrambled payload of the block: a whole
number, or a string that Python's ``int(text, 0)`` reads. ``count`` is
optional; without it any number of copies is accepted, except none.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, TypeVar, Union

from .container import parse, serialize
from .errors import ContainerError, SpecError
from .fileio import read_json
from .hashing import is_sha256, sha256_bytes

UTF16 = "utf-16-le"
_UTF16_UNIT = 2
_COMPARE_CHUNK = 1 << 16

T = TypeVar("T")


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
    """Replace every copy of a UTF-16 text with another text of the same length.

    A copy counts if it starts on an even offset. Copies are found from the
    start of the block and do not overlap: the search goes on after the end of
    each copy.

    Attributes:
        block: index of the container block.
        old: the text to find.
        new: the text to write; same number of UTF-16 bytes as ``old``.
        count: how many copies there must be, or None to accept one or more.
    """

    block: int
    old: str
    new: str
    count: int | None

    def describe(self) -> str:
        """Return a one-line description of the operation."""
        return f"block{self.block}: '{self.old}' -> '{self.new}'"


Op = Union[BytesOp, Utf16ReplaceAllOp]


@dataclass(frozen=True)
class PatchSpec:
    """A patch spec.

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
    ops: tuple[Op, ...]
    expected_sha256: str | None = None
    source: Path | None = None


def _require(mapping: Mapping[str, Any], key: str, kind: type[T], where: str) -> T:
    """Return ``mapping[key]`` after checking that it is there and of type ``kind``.

    A JSON true or false is never accepted as a number.
    """
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


def _offset(mapping: Mapping[str, Any], where: str) -> int:
    """Return the ``offset`` field: a whole number, or a string of one."""
    if "offset" not in mapping:
        raise SpecError(f"{where}: missing 'offset'")
    raw = mapping["offset"]
    if isinstance(raw, str):
        try:
            value = int(raw, 0)
        except ValueError:
            raise SpecError(f"{where}: 'offset' is not a number: {raw!r}") from None
    elif isinstance(raw, int) and not isinstance(raw, bool):
        value = raw
    else:
        raise SpecError(f"{where}: 'offset' must be a whole number, got {raw!r}")
    if value < 0:
        raise SpecError(f"{where}: 'offset' must not be negative")
    return value


def _utf16(text: str, key: str, where: str) -> bytes:
    """Return ``text`` as UTF-16 bytes."""
    try:
        return text.encode(UTF16)
    except UnicodeEncodeError as error:
        raise SpecError(
            f"{where}: '{key}' cannot be written as UTF-16: {error}"
        ) from None


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
        offset = _offset(raw, where)
        expect, new = _hex(raw, "expect", where), _hex(raw, "new", where)
        if len(expect) != len(new):
            raise SpecError(
                f"{where}: 'expect' has {len(expect)} bytes and 'new' has {len(new)}"
            )
        if not new:
            raise SpecError(f"{where}: 'expect' and 'new' are empty")
        return BytesOp(block, offset, expect, new)
    if kind == "utf16-replace-all":
        old = _require(raw, "old", str, where)
        new_text = _require(raw, "new", str, where)
        if not old:
            raise SpecError(f"{where}: 'old' is empty")
        if len(_utf16(old, "old", where)) != len(_utf16(new_text, "new", where)):
            raise SpecError(f"{where}: '{old}' and '{new_text}' differ in length")
        count = raw.get("count")
        if count is not None and (
            not isinstance(count, int) or isinstance(count, bool) or count < 1
        ):
            raise SpecError(f"{where}: 'count' must be a whole number of 1 or more")
        return Utf16ReplaceAllOp(block, old, new_text, count)
    raise SpecError(f"{where}: unknown operation type '{kind}'")


def spec_from_json(raw: Any, source: Path | None = None) -> PatchSpec:
    """Build a patch spec from its JSON form.

    Args:
        raw: the parsed JSON.
        source: the file it came from, for error messages.

    Raises:
        SpecError: if the JSON is not a valid spec.
    """
    where = str(source) if source else "spec"
    if not isinstance(raw, Mapping):
        raise SpecError(f"{where}: a spec must be a JSON object")
    name = _require(raw, "name", str, where)
    ops = []
    for index, item in enumerate(_require(raw, "ops", list, where)):
        op_where = f"{where}: op {index}"
        if not isinstance(item, Mapping):
            raise SpecError(f"{op_where}: an operation must be a JSON object")
        ops.append(op_from_json(item, op_where))
    base_sha256 = _require(raw, "base_sha256", str, where)
    if not is_sha256(base_sha256):
        raise SpecError(f"{where}: 'base_sha256' must be 64 lower-case hex digits")
    expected = raw.get("expected_sha256")
    if expected is not None and not is_sha256(expected):
        raise SpecError(f"{where}: 'expected_sha256' must be 64 lower-case hex digits")
    description = raw.get("description", "")
    if not isinstance(description, str):
        raise SpecError(f"{where}: 'description' must be str")
    return PatchSpec(
        name=name,
        description=description,
        base=_require(raw, "base", str, where),
        base_sha256=base_sha256,
        ops=tuple(ops),
        expected_sha256=expected,
        source=source,
    )


def load_spec(path: Path) -> PatchSpec:
    """Read a patch spec file.

    Raises:
        SpecError: if the file is missing, is not JSON, or is not a valid spec.
    """
    return spec_from_json(read_json(path, SpecError), path)


def _aligned_hits(payload: bytearray, old: bytes) -> list[int]:
    """Return the even offsets of the copies of ``old``, left to right, not overlapping."""
    hits: list[int] = []
    position = payload.find(old)
    while position >= 0:
        if position % _UTF16_UNIT == 0:
            hits.append(position)
            position = payload.find(old, position + len(old))
        else:
            position = payload.find(old, position + 1)
    return hits


def apply_op(payloads: list[bytearray], op: Op) -> str:
    """Apply one operation to the payloads, in place.

    Args:
        payloads: the unscrambled payload of every block of the container.
        op: the operation.

    Returns:
        A line of text that says what was done.

    Raises:
        SpecError: if the block does not exist, the bytes to replace are not
            the expected ones, a text has no copy, or the number of copies is
            not the stated one. Nothing is changed then.
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
    hits = _aligned_hits(payload, old)
    if not hits:
        raise SpecError(f"'{op.old}': no copy found in block {op.block}")
    if op.count is not None and len(hits) != op.count:
        raise SpecError(
            f"'{op.old}': found {len(hits)} copies in block {op.block}, "
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
    log: tuple[str, ...]
    changed_bytes: int


def count_differences(first: bytes, second: bytes) -> int:
    """Return how many positions of two byte strings of the same length differ."""
    if len(first) != len(second):
        raise ValueError("the two byte strings differ in length")
    total = 0
    for start in range(0, len(first), _COMPARE_CHUNK):
        a = first[start : start + _COMPARE_CHUNK]
        b = second[start : start + _COMPARE_CHUNK]
        if a != b:
            total += sum(x != y for x, y in zip(a, b))
    return total


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
        ContainerError: if ``stock`` is not a firmware container, or one of its
            checksums is wrong.
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
    container = parse(stock)
    if not container.checksums_ok:
        raise ContainerError("the stock firmware has a block with a wrong checksum")
    payloads = [bytearray(block.payload) for block in container.blocks]
    log: list[str] = []
    for spec in specs:
        log.append(f"[{spec.name}]")
        for index, op in enumerate(spec.ops):
            try:
                log.append("  " + apply_op(payloads, op))
            except SpecError as error:
                raise SpecError(f"{spec.name} op {index}: {error}") from None
    image = serialize(container.with_payloads([bytes(p) for p in payloads]))
    return Applied(image, tuple(log), count_differences(stock, image))


def op_to_json(op: Op) -> dict[str, Any]:
    """Return the JSON form of an operation."""
    if isinstance(op, BytesOp):
        return {
            "type": "bytes",
            "block": op.block,
            "offset": hex(op.offset),
            "expect": op.expect.hex(),
            "new": op.new.hex(),
        }
    raw: dict[str, Any] = {
        "type": "utf16-replace-all",
        "block": op.block,
        "old": op.old,
        "new": op.new,
    }
    if op.count is not None:
        raw["count"] = op.count
    return raw
