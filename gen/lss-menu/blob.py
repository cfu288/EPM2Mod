"""A language blob of block 1: the texts of one menu language by string id."""

import struct

BLOCK1_LOAD = 0x43C40000
RUNTIME = 0xBFF3D000
N_IDS = 1970


class Blob:
    """One language blob of a block-1 payload."""

    def __init__(self, data: bytes, entry: int) -> None:
        address, size = struct.unpack_from("<2I", data, 16 * entry)
        start = address - BLOCK1_LOAD
        for head in range(start - 0x200, start + 0x200, 2):
            first, end = struct.unpack_from("<2I", data, head)
            if RUNTIME < first < end < RUNTIME + 0x80000 and end - first == 4 * N_IDS:
                if struct.unpack_from("<I", data, head + first - RUNTIME)[0] == RUNTIME + 8:
                    break
        else:
            raise SystemExit(f"language {entry}: no blob header found")
        self.data, self.entry, self.head = data, entry, head
        self.array = head + first - RUNTIME
        self.pointers = list(struct.unpack_from(f"<{N_IDS}I", data, self.array))
        foot = data[self.array + 4 * N_IDS : start + size].decode("utf-16-le", "replace")
        self.code = foot.split("OlympusLanguage_")[1][:3] if "OlympusLanguage_" in foot else "?"

    def offset(self, string_id: int) -> int:
        """Return the block offset of the text of an id."""
        return self.head + self.pointers[string_id] - RUNTIME

    def text(self, string_id: int) -> str:
        """Return the text of an id."""
        start = end = self.offset(string_id)
        while self.data[end : end + 2] != b"\0\0":
            end += 2
        return self.data[start:end].decode("utf-16-le")
