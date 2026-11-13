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

``status``, ``attribution`` and ``inputs_sha256`` are notes that other tools and
people write; they are accepted and not read here. So is any key that starts
with ``_``, in a spec or in an operation. Every other unknown key is an error,
so a misspelt key cannot silently switch a check off.

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
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, Union

from .container import parse, serialize
from .errors import ContainerError, SpecError
from .fileio import read_json
from .hashing import is_sha256, sha256_bytes

UTF16 = "utf-16-le"
_UTF16_UNIT = 2
_COMPARE_CHUNK = 1 << 16
#: Keys that start with this are notes for people; they are never read.
NOTE_PREFIX = "_"
_SPEC_KEYS = {"name", "description", "base", "base_sha256", "ops", "expected_sha256"}
_SPEC_NOTE_KEYS = {"status", "attribution", "inputs_sha256"}
_BYTES_KEYS = {"type", "block", "offset", "expect", "new"}
_TEXT_KEYS = {"type", "block", "old", "new", "count"}

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

    def __post_init__(self) -> None:
        """Check the operation. Every instance is valid.

        Raises:
            SpecError: if a number is negative, the two byte strings differ in
                length, or they are empty.
        """
        if self.block < 0 or self.offset < 0:
            raise SpecError(
                "a bytes operation needs a block and an offset of 0 or more"
            )
        if len(self.expect) != len(self.new):
            raise SpecError(
                f"'expect' has {len(self.expect)} bytes and 'new' has {len(self.new)}"
            )
        if not self.new:
            raise SpecError("'expect' and 'new' are empty")

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

    def __post_init__(self) -> None:
        """Check the operation. Every instance is valid.

        Raises:
            SpecError: if the block is negative, a text cannot be written as
                UTF-16, the texts are empty or differ in length, or the count
                is less than 1.
        """
        if self.block < 0:
            raise SpecError("a text operation needs a block of 0 or more")
        try:
            old, new = self.old.encode(UTF16), self.new.encode(UTF16)
        except UnicodeEncodeError as error:
            raise SpecError(f"a text cannot be written as UTF-16: {error}") from None
        if not old:
            raise SpecError("'old' is empty")
        if len(old) != len(new):
            raise SpecError(f"'{self.old}' and '{self.new}' differ in length")
        if self.count is not None and self.count < 1:
            raise SpecError("'count' must be 1 or more")

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
        base: a note for people: the stock firmware file the spec is for. It
            is not read; ``base_sha256`` is what ties a spec to its firmware.
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

    def __post_init__(self) -> None:
        """Check the two SHA-256 fields.

        Raises:
            SpecError: if one of them is not 64 lower-case hexadecimal digits.
        """
        if not is_sha256(self.base_sha256):
            raise SpecError("'base_sha256' must be 64 lower-case hex digits")
        if self.expected_sha256 is not None and not is_sha256(self.expected_sha256):
            raise SpecError("'expected_sha256' must be 64 lower-case hex digits")


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


def _closed(raw: Mapping[str, Any], allowed: set[str], where: str) -> None:
    """Raise if ``raw`` has a key that is not allowed and is not a note."""
    unknown = sorted(
        key for key in raw if key not in allowed and not key.startswith(NOTE_PREFIX)
    )
    if unknown:
        raise SpecError(f"{where}: unknown key(s): {', '.join(unknown)}")


def op_from_json(raw: Mapping[str, Any], where: str) -> Op:
    """Build one operation from its JSON form.

    Args:
        raw: the JSON object of the operation.
        where: text that names the operation in error messages.

    Raises:
        SpecError: if a field is missing, wrong or unknown, or the type is not
            known.
    """
    kind = _require(raw, "type", str, where)
    block = _require(raw, "block", int, where)
    try:
        if kind == "bytes":
            _closed(raw, _BYTES_KEYS, where)
            return BytesOp(
                block,
                _offset(raw, where),
                _hex(raw, "expect", where),
                _hex(raw, "new", where),
            )
        if kind == "utf16-replace-all":
            _closed(raw, _TEXT_KEYS, where)
            count = raw.get("count")
            if count is not None and (
                not isinstance(count, int) or isinstance(count, bool)
            ):
                raise SpecError("'count' must be a whole number")
            return Utf16ReplaceAllOp(
                block,
                _require(raw, "old", str, where),
                _require(raw, "new", str, where),
                count,
            )
    except SpecError as error:
        text = str(error)
        raise SpecError(
            text if text.startswith(where) else f"{where}: {text}"
        ) from None
    raise SpecError(f"{where}: unknown operation type '{kind}'")


def spec_from_json(raw: Any, source: Path | None = None) -> PatchSpec:
    """Build a patch spec from its JSON form.

    Args:
        raw: the parsed JSON.
        source: the file it came from, for error messages.

    Raises:
        SpecError: if the JSON is not a valid spec, or has an unknown key.
    """
    where = str(source) if source else "spec"
    if not isinstance(raw, Mapping):
        raise SpecError(f"{where}: a spec must be a JSON object")
    _closed(raw, _SPEC_KEYS | _SPEC_NOTE_KEYS, where)
    name = _require(raw, "name", str, where)
    ops = []
    for index, item in enumerate(_require(raw, "ops", list, where)):
        op_where = f"{where}: op {index}"
        if not isinstance(item, Mapping):
            raise SpecError(f"{op_where}: an operation must be a JSON object")
        ops.append(op_from_json(item, op_where))
    description = raw.get("description", "")
    if not isinstance(description, str):
        raise SpecError(f"{where}: 'description' must be str")
    expected = raw.get("expected_sha256")
    if expected is not None and not isinstance(expected, str):
        raise SpecError(f"{where}: 'expected_sha256' must be str")
    try:
        return PatchSpec(
            name=name,
            description=description,
            base=_require(raw, "base", str, where),
            base_sha256=_require(raw, "base_sha256", str, where),
            ops=tuple(ops),
            expected_sha256=expected,
            source=source,
        )
    except SpecError as error:
        text = str(error)
        raise SpecError(
            text if text.startswith(where) else f"{where}: {text}"
        ) from None


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
