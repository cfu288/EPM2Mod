# Audit A12: 09b re-audit

## 09b-57 (sections/09b-art-algorithms.md, line 57)

- **Verified:** op type 21 (desc+194) is the same image-engine job that `[movp]copy` 0x7E6E3161 uses. So it is a

## 09b-61 (sections/09b-art-algorithms.md, line 61)

- **Masks (`make_mask` 0x7E548626 → 0x7E54846F, verified).** Each mask is radially symmetric:

## 09b-76 (sections/09b-art-algorithms.md, line 76)

- **Verified:** `art_chk_type_rec` 0x7E71C0E1 (trace id 7; its caller `art_chk_type` 0x7E71C075 is id 6) accepts 151/153 only when req+2==3 (block 0x7E71C1BA). (A10 2026-11-09)

## 09b-141 (sections/09b-art-algorithms.md, line 141)

- **Verified:** the filter hash entry for 118 (table 0x7E85C45C, key 0x2E) → case 0x7E72A635 → 0x7E71E705. This

## 09b-145 (sections/09b-art-algorithms.md, line 145)

- **Verified:** the star module range 0x7E71E705–0x7E72032F contains no compare with 118. Its `(6,aX)` reads are

## 09b-148 (sections/09b-art-algorithms.md, line 148)

- ~~**Verified:** I searched the image-engine driver (0x7E54xxxx–0x7E56xxxx) for compares on P+79. It branches on 96/97/165/166, 151/152 and 181–184. It does **not** branch on 118.~~ (A11 2026-11-09)

## 09b-149 (sections/09b-art-algorithms.md, line 149)

- **Verified (A11 2026-11-09):** the image-engine driver (0x7E540000–0x7E56FFFF) has no literal `cmp 118`, and none of the five P+79 hashes (0x7E78B29C, 0x7E74A568, 0x7E78CBA8, 0x7E78CCA8, 0x7E78CDA8) has key 118. But P+79 (P = desc+96) also feeds **three jump tables that give {118, 122} a case of their own** (122 = the movie-side Sparkle code, `mov_art` table 0x7E7FF008, 09a). Each case loads its own parameter pointer: (A11 2026-11-09)

## 09b-157 (sections/09b-art-algorithms.md, line 157)

- **Verified:** `art_chk_type_rec` (0x7E71C0E1) accepts 118 for req+2 = 1 and 3, but not 2. (A10 2026-11-09)

