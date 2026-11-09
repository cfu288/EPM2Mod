# Audit A8 batch 3 (15c)

## 15c-48 (sections/15c-app-statecharts.md, line 48)

| +680 | 0x7EB3DC53 / 0x7EC79354 | 0x7EB3DC6E | 7604 |

## 15c-49 (sections/15c-app-statecharts.md, line 49)

| +704 | 0x7EB3DCB9 / 0x7EC79370 | 0x7EB3DCDA (118 B: reads a progress value first, §3.2) | 7605 |

## 15c-73 (sections/15c-app-statecharts.md, line 73)

| **7609** | **`evTraCmpPly_NotifySelectExecuteEnd`** (V: CmpEAsp `save_start_enter` 0x7EABA04C tests only 7609 and logs it) | 0x7EB0F0D2, CmpPLgh 0x7EB33E6E, CmpPSel 0x7EB4FA8E | consumed by the work state that waits for the redraw (138 test sites), e.g. erase state 37 (F045) |

## 15c-93 (sections/15c-app-statecharts.md, line 93)

| 8 (0x7EA7E198) | 12063 → 7 | GEN 4761 boot request to +472 |

## 15c-106 (sections/15c-app-statecharts.md, line 106)

| 1 → 39 `play_service_end` 0x7EB1669D · 2 → 31 `get_image_type` 0x7EB16263 · 3 → 23 `get_still_info` 0x7EB15FF7 · 4 → 29 `get_move_info` 0x7EB161EC · 5 → 27 `get_number` 0x7EB16175 · 6 → 33 `get_image_count` 0x7EB162DA · 7 → 35 `get_histogram` 0x7EB16351 |

## 15c-121 (sections/15c-app-statecharts.md, line 121)

| 1 (0x7EB785F8) | GEN 11565 to self | 11565 → 3 (inline in the dispatcher) |

## 15c-122 (sections/15c-app-statecharts.md, line 122)

| 3 Idle (0x7EB78E44) | — | 11761 → 8 |

## 15c-162 (sections/15c-app-statecharts.md, line 162)

| CmpSts_MultiThrough 0x7EB7EC0B | 0x7EB7ED19 | 11980, 11979, 11978 (startMultiThrough), 12004, 12005 |

## 15c-166 (sections/15c-app-statecharts.md, line 166)

| the other 8 (3D, EPortrait, RecView, Record, Outline 0x7EA7E6EB, the getName-less subclasses 0x7EA6CF32 / 0x7EA77CBA, Com_ActiveTransitionManagerBufferd 0x7EB8AD37) | 0x7EB85924 (empty) or a stub | none |

