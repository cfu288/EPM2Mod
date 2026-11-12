"""Olympus ORF compressed raw (12-bit) codec: decoder ported from dcraw's olympus_load_raw, and the
matching encoder. Used to write a synthetic test image the camera can re-develop (NOTES §24).
The raw strip is: 7 header bytes, then one MSB-first bit stream for all rows."""
import numpy as np
from numba import njit


@njit(cache=True)
def _pred(img, row, col):
    if row < 2 and col < 2:
        return 0
    if row < 2:
        return int(img[row, col - 2])
    if col < 2:
        return int(img[row - 2, col])
    w = int(img[row, col - 2]); n = int(img[row - 2, col]); nw = int(img[row - 2, col - 2])
    if (w < nw and nw < n) or (n < nw and nw < w):
        if abs(w - nw) > 32 or abs(n - nw) > 32:
            return w + n - nw
        return (w + n) >> 1
    return w if abs(w - nw) > abs(n - nw) else n


@njit(cache=True)
def decode(data, height, width):
    img = np.zeros((height, width), np.int32)
    pos = 7 * 8                                   # bit position
    nbytes = len(data)

    def bits(n, pos):
        v = 0
        for _ in range(n):
            byte = data[pos >> 3] if (pos >> 3) < nbytes else 0
            v = (v << 1) | ((byte >> (7 - (pos & 7))) & 1)
            pos += 1
        return v, pos

    for row in range(height):
        acarry = np.zeros((2, 3), np.int64)
        for col in range(width):
            carry = acarry[col & 1]
            i = 2 if carry[2] < 3 else 0
            nbits = 2 + i
            while ((carry[0] & 0xFFFF) >> (nbits + i)) != 0:
                nbits += 1
            s3, pos = bits(3, pos)
            low = s3 & 3
            sign = -1 if (s3 & 4) else 0
            high = 0
            while high < 12:
                b, pos = bits(1, pos)
                if b:
                    break
                high += 1
            if high == 12:
                h, pos = bits(16 - nbits, pos)
                high = h >> 1
            lowpart, pos = bits(nbits, pos)
            carry[0] = (high << nbits) | lowpart
            diff = (carry[0] ^ sign) + carry[1]
            carry[1] = (diff * 3 + carry[1]) >> 5
            carry[2] = 0 if carry[0] > 16 else carry[2] + 1
            img[row, col] = _pred(img, row, col) + ((diff << 2) | low)
    return img


@njit(cache=True)
def encode(img):
    height, width = img.shape
    out = np.zeros(height * width * 3 + 64, np.uint8)        # generous: <= 24 bits per pixel
    pos = 7 * 8

    def put(v, n, pos):
        for k in range(n - 1, -1, -1):
            if (v >> k) & 1:
                out[pos >> 3] |= 1 << (7 - (pos & 7))
            pos += 1
        return pos

    for row in range(height):
        acarry = np.zeros((2, 3), np.int64)
        for col in range(width):
            carry = acarry[col & 1]
            i = 2 if carry[2] < 3 else 0
            nbits = 2 + i
            while ((carry[0] & 0xFFFF) >> (nbits + i)) != 0:
                nbits += 1
            total = int(img[row, col]) - _pred(img, row, col)
            low = total & 3
            diff = total >> 2
            x = diff - carry[1]
            if x < 0:
                sign = -1; c0 = -x - 1
            else:
                sign = 0; c0 = x
            pos = put((4 if sign else 0) | low, 3, pos)
            high = c0 >> nbits
            if high < 12:
                pos = put(1, high + 1, pos)                  # 'high' zeros, then a one
            else:
                pos = put(0, 12, pos)
                pos = put((high << 1) | 1, 16 - nbits, pos)      # the camera sets the unused last bit
            pos = put(c0 & ((1 << nbits) - 1), nbits, pos)
            carry[0] = c0
            carry[1] = (diff * 3 + carry[1]) >> 5
            carry[2] = 0 if c0 > 16 else carry[2] + 1
    return out[:(pos + 7) >> 3]
