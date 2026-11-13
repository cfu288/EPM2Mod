"""The Olympus "OE" firmware container.

A firmware file is a sequence of blocks followed by an opaque tail (the image
of a second, small processor). Each block is::

    header   32 bytes   'OE', model, ..., load address at 8, payload length at 12,
                        kind at 20 (all little-endian)
    payload  N bytes    scrambled: the 16 bytes of each row are permuted by
                        ``LANES`` and then inverted (XOR 0xFF)
    trailer  32 bytes   a copy of the first 28 header bytes, then a checksum word

The checksum word makes the sum of all little-endian 32-bit words of the
header, the *unscrambled* payload and the trailer equal to zero modulo 2**32.

The format was worked out on the E-PM2 (model 1010) and checked by a byte-exact
round trip of six firmware versions.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, replace
from collections.abc import Sequence

from .errors import ContainerError
from .hashing import sha256_bytes

#: Position, in a scrambled 16-byte row, of each byte of the plain row.
LANES = (1, 3, 0, 2, 6, 4, 7, 5, 11, 10, 9, 8, 13, 14, 12, 15)
MAGIC = b"OE"
HEADER_SIZE = 32
TRAILER_SIZE = 32
ROW = 16
_WORD_MASK = 0xFFFFFFFF
_INVERT = bytes(range(255, -1, -1))


def descramble(data: bytes) -> bytes:
    """Turn a scrambled payload into plain bytes.

    Args:
        data: scrambled payload; its length must be a multiple of 16.

    Returns:
        The plain payload, of the same length.
    """
    out = bytearray(len(data))
    for plain_lane, scrambled_lane in enumerate(LANES):
        out[plain_lane::ROW] = data[scrambled_lane::ROW].translate(_INVERT)
    return bytes(out)


def scramble(data: bytes) -> bytes:
    """Turn plain bytes into a scrambled payload. Inverse of ``descramble``."""
    out = bytearray(len(data))
    for plain_lane, scrambled_lane in enumerate(LANES):
        out[scrambled_lane::ROW] = data[plain_lane::ROW].translate(_INVERT)
    return bytes(out)


def word_sum(data: bytes) -> int:
    """Return the sum of the little-endian 32-bit words of ``data``, modulo 2**32.

    Raises:
        ContainerError: if the length is not a multiple of 4.
    """
    if len(data) % 4:
        raise ContainerError(f"length {len(data)} is not a multiple of 4")
    words: tuple[int, ...] = struct.unpack(f"<{len(data) // 4}I", data)
    return sum(words) & _WORD_MASK


@dataclass(frozen=True)
class Block:
    """One block of a firmware container.

    Attributes:
        offset: position of the block's header in the file.
        header: the 32 header bytes, as stored.
        trailer: the 32 trailer bytes, as stored.
        payload: the payload, unscrambled.
        checksum_ok: True if the stored checksum fits header, payload and trailer.
    """

    offset: int
    header: bytes
    trailer: bytes
    payload: bytes
    checksum_ok: bool

    def __post_init__(self) -> None:
        """Check the sizes of the parts. Every instance can be serialized.

        Raises:
            ContainerError: if the header or the trailer has the wrong size, or
                the payload length is not a multiple of 16.
        """
        if len(self.header) != HEADER_SIZE or len(self.trailer) != TRAILER_SIZE:
            raise ContainerError(
                f"block at {self.offset:#x}: the header and the trailer must be "
                f"{HEADER_SIZE} and {TRAILER_SIZE} bytes"
            )
        if len(self.payload) % ROW:
            raise ContainerError(
                f"block at {self.offset:#x}: payload length {len(self.payload)} "
                f"is not a multiple of {ROW}"
            )

    @property
    def load_address(self) -> int:
        """The address field of the header."""
        return int(struct.unpack_from("<I", self.header, 8)[0])

    @property
    def declared_length(self) -> int:
        """The payload length that the header states."""
        return int(struct.unpack_from("<I", self.header, 12)[0])

    @property
    def kind(self) -> int:
        """The kind field of the header (0x0100 is the main program)."""
        return int(struct.unpack_from("<H", self.header, 20)[0])

    def with_payload(self, payload: bytes) -> Block:
        """Return a copy of the block with another payload of the same length.

        The checksum of the copy is not valid until the container is
        serialized, which computes it again.

        Raises:
            ContainerError: if the length differs. Blocks cannot be resized.
        """
        if len(payload) != len(self.payload):
            raise ContainerError(
                f"block at {self.offset:#x}: payload length would change from "
                f"{len(self.payload)} to {len(payload)}; blocks cannot be resized"
            )
        return replace(self, payload=bytes(payload), checksum_ok=False)


@dataclass(frozen=True)
class Container:
    """A parsed firmware file.

    Attributes:
        blocks: the blocks, in file order.
        tail: the bytes after the last block, unchanged.
    """

    blocks: tuple[Block, ...]
    tail: bytes

    @property
    def checksums_ok(self) -> bool:
        """True if every block's stored checksum is right."""
        return all(block.checksum_ok for block in self.blocks)

    def with_payloads(self, payloads: Sequence[bytes]) -> Container:
        """Return a copy with new payloads, one per block, of unchanged lengths."""
        if len(payloads) != len(self.blocks):
            raise ContainerError(
                f"{len(payloads)} payloads for {len(self.blocks)} blocks"
            )
        blocks = [
            block if payload == block.payload else block.with_payload(payload)
            for block, payload in zip(self.blocks, payloads)
        ]
        return Container(tuple(blocks), self.tail)


def parse(data: bytes) -> Container:
    """Parse a firmware file.

    Args:
        data: the whole file.

    Returns:
        The blocks, with unscrambled payloads, and the tail.

    The tail is everything after the last block. Its content is not checked:
    the container has no checksum for it, so only a SHA-256 of the whole file
    shows a damaged tail.

    Raises:
        ContainerError: if the file does not start with a block, or it ends
            inside a block, or a payload length is not a multiple of 16.
    """
    blocks: list[Block] = []
    offset = 0
    minimum = HEADER_SIZE + TRAILER_SIZE
    while data[offset : offset + 2] == MAGIC:
        if offset + minimum > len(data):
            raise ContainerError(
                f"block at {offset:#x}: the file ends inside the block's header"
            )
        header = data[offset : offset + HEADER_SIZE]
        length = int(struct.unpack_from("<I", header, 12)[0])
        if length % ROW:
            raise ContainerError(
                f"block at {offset:#x}: payload length {length} is not a "
                f"multiple of {ROW}"
            )
        end = offset + minimum + length
        if end > len(data):
            raise ContainerError(
                f"block at {offset:#x}: needs {end - len(data)} more bytes than "
                "the file has"
            )
        payload = descramble(data[offset + HEADER_SIZE : offset + HEADER_SIZE + length])
        trailer = data[end - TRAILER_SIZE : end]
        total = word_sum(header) + word_sum(payload) + word_sum(trailer)
        blocks.append(Block(offset, header, trailer, payload, total & _WORD_MASK == 0))
        offset = end
    if not blocks:
        raise ContainerError("not a firmware container: no block at the start")
    return Container(tuple(blocks), data[offset:])


def serialize(container: Container) -> bytes:
    """Write a container back to bytes, with fresh checksums.

    A container that was parsed from a file with right checksums, and not
    changed, serializes to the bytes it was parsed from. A block whose stored
    checksum was wrong gets a right one: check ``checksums_ok`` before you
    serialize if the input must be sound.

    Raises:
        ContainerError: if a payload's length differs from the length in its header.
    """
    out = bytearray()
    for block in container.blocks:
        if block.declared_length != len(block.payload):
            raise ContainerError(
                f"block at {block.offset:#x}: header says {block.declared_length} "
                f"bytes, payload has {len(block.payload)}"
            )
        trailer = bytearray(block.trailer)
        trailer[28:32] = bytes(4)
        partial = (
            word_sum(block.header) + word_sum(block.payload) + word_sum(bytes(trailer))
        )
        struct.pack_into("<I", trailer, 28, (-partial) & _WORD_MASK)
        out += block.header + scramble(block.payload) + trailer
    return bytes(out + container.tail)


def describe(container: Container) -> list[str]:
    """Return one line of text per block of a container, and one for the tail."""
    lines = [
        f"block{index} @{block.offset:#010x} kind={block.kind:#06x} "
        f"addr={block.load_address:#010x} len={len(block.payload)} "
        f"checksum={'OK' if block.checksum_ok else 'BAD'}"
        for index, block in enumerate(container.blocks)
    ]
    lines.append(
        f"tail len={len(container.tail)} sha256={sha256_bytes(container.tail)[:16]}"
    )
    return lines
