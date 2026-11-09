# Audit A8 batch 4 (15d)

## 15d-40 (sections/15d-protocols-platform.md, line 40)

| 0x7E923928–0x7E924003 | Olympus test client | 0x602AE, 0x605D0–5 | `OLYMPUS BlueSDK a4`, BTAPL task 0x7E923FD2, demo-shell entries 0x7E923C93–0x7E923FFB (V) |

## 15d-73 (sections/15d-protocols-platform.md, line 73)

- **Link control** 0x0401–0x0434 (Inquiry, Create Connection, Disconnect, accept/reject, link-key/PIN/passkey/confirm/OOB replies, authentication, encryption, remote name and features);

## 15d-93 (sections/15d-protocols-platform.md, line 93)

- **Link records at 0x7DAC4C68, stride 320.** All 3 loops (0x7E9275C6 find by BD_ADDR, 0x7E927600 allocate, 0x7E927681 find by handle) stop at `cmp 1`. So **there is exactly one record**: the stack supports one ACL link (V). The record starts with the op node, so for link commands curOp is the record. Fields:

## 15d-102 (sections/15d-protocols-platform.md, line 102)

| +146 | in-use / state (0 = free) | allocator, free 0x7E927679 |

## 15d-199 (sections/15d-protocols-platform.md, line 199)

- Range helper 0x7F061CED (13 callers).

## 15d-228 (sections/15d-protocols-platform.md, line 228)

- **Section 01 is right that A and B are separate Usr2 requests.** Usr2 0x7E505005 tests `btst 1` → overlay A (0xF000 B from 0x80EFB000 to 0xBF05C000, segment-4 constructors, USTART3), `btst 2` → overlay B (0x6B800 B from 0x80F1F000 to 0xBF080000, segment 5, USTART4) and `and 0x1000000` → ADJSLF; done flags in 0x602A9B48.

## 15d-244 (sections/15d-protocols-platform.md, line 244)

| 0x7E45038D–0x7E450C4A | **SYSFMEM operation bodies** (BML read variants and retry, write/erase with read-back, STL thunks 0x7E450AA1–0x7E450AD3, boot-bank check 0x7E450C4B) | SYSFMEM 0x7E4520F3; `flash` shell | V |

## 15d-245 (sections/15d-protocols-platform.md, line 245)

| 0x7E45140B–0x7E4520F2 | second request poster 0x7E45140B, `prm fmem` 0x7E451515/0x7E4515F5, **traced BML/STL wrappers** 0x7E451873–0x7E451D85 (STL_READ = C3 F001) | fupsrv 0x7E54398B, ADJ | V |

## 15d-286 (sections/15d-protocols-platform.md, line 286)

1. **05 row "~0x7E91D279–~0x7E937CDD Blue SDK".** The stack also has part 1 at 0x7E915A1B–0x7E91962B (init, EVM, profiles, the **HCI layer**). That part sits inside 05's row "0x7E913984–0x7E91CFFF stack callbacks, iAP". Also, 0x7E91D279/0x7E91D289 are iAP getters; L2CAP starts at 0x7E91D29F (V).

