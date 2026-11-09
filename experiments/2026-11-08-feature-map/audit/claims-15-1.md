# Audit A8 batch 1 (15a)

## 15a-42 (sections/15a-gui-pages.md, line 42)

- **`openPage(id)` 0x7EDCBE97.** Callers do not call it directly. They allocate a 4-byte functor, store the vtable 0x7EFD51D0 (byte signature `fc cc d0 51 fd 7e`) and call vt[0] with the page id (22 sites).

## 15a-54 (sections/15a-gui-pages.md, line 54)

- The grand-base is 0x7EDCCA5D (vt 0x7EFE6214, 30 slots). The **page base** is 0x7EDCD621 (vt 0x7EFE79FC, 32 slots, 96 callers).

## 15a-59 (sections/15a-gui-pages.md, line 59)

| 0x7EDC7EAA | **userCommonSecondWizard**: the generic list page. +168 = list id, +172 = list descriptor | 0x7EFE221C | 1,748 B | factory 0x7EDC7ECB serves 110 list ids; 29 derived classes |

## 15a-63 (sections/15a-gui-pages.md, line 63)

| 0x7EDED9DD | userCommonWizard1NRightAligned | 0x7EFFE768 | 1,756 B | the play/edit wizards |

## 15a-100 (sections/15a-gui-pages.md, line 100)

- **`getListDescriptor(N)` 0x7EDFD9AF.** It searches 312 × `{u16 list id, u32 desc}` at **0x7F00D710**.

## 15a-123 (sections/15a-gui-pages.md, line 123)

| Page dtor | `f8 fe fc dd → 0x7EDCD664 ; 90 00 ; df 00 04` | — |

## 15a-133 (sections/15a-gui-pages.md, line 133)

| 511 / 513 | 0x7EDE437F / 0x7EDE4632 (168 B each) | PENPAL album copy P2S / S2P. Panel 4; MediaCtrl vt+44 with (2,4) / (4,2). The sibling pages 515, 519, 521 and 493 are also 168-B MediaCtrl pages |

## 15a-134 (sections/15a-gui-pages.md, line 134)

| 466 | 0x7EDFB664, vt 0x7F004DC0 | `userMenuRec2_CompScale`. Panel 64; moveCurrent 0x7EDFB968 |

## 15a-146 (sections/15a-gui-pages.md, line 146)

- key slot 0x7EDFD86F: key 10 with d1 = 0 sets the flag +168, and any other d1 clears it; OK returns 3 only if the flag is set **and** `IOlyApiMaintenance` vt+40 = 1;

