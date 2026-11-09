# Audit A9 batch 2 (15c)

## 15c-16 (sections/15c-app-statecharts.md, line 16)

| 0x7EB2887C–0x7EB2BB80 | `CmpPEvV_PlayEventViewComponent` (getInstance 0x7EB2887C; `rcv Request` dispatcher 0x7EB2B6C8 is inside) |

## 15c-22 (sections/15c-app-statecharts.md, line 22)

| 0x7EB8C265–0x7EB93422 | Dev part 1: 14 device units, §5 |

## 15c-51 (sections/15c-app-statecharts.md, line 51)

| +680 | 0x7EB3DC53 / 0x7EC79354 | 0x7EB3DC6E | 7604 |

## 15c-57 (sections/15c-app-statecharts.md, line 57)

2. **Subscription.** `app_select_display_execute` 0x7EB0B054 (`Cmp_PlayComponentBase.cpp`, 81 callers) registers the members with the EVFW router (14c §2.4). +680 is registered with **11775** for a request handle; +656 is subscribed (11776) to APP_EVENT code 0x02020002 and +732 to 0x03010005. +584 is subscribed to 0x04020181 in 0x7EB0ED3C. +756/+780/+804 sit on CapDpv (+828) notification lists: 0x7EB12BD9 (9 callers, the unsubscribe step) removes them via CapDpv iface slots 31/32/33 (vt+124/+128/+132), then calls CM unsubscribe 0x7EA7DB1E.

## 15c-96 (sections/15c-app-statecharts.md, line 96)

| 8 (0x7EA7E198) | 12063 → 7 | GEN 4761 boot request to +472 |

## 15c-132 (sections/15c-app-statecharts.md, line 132)

| 4 (0x7EB78EEA) | — | 11769 → 1; CM-type ids 13363–13365, 11566, 11761, 12962 |

## 15c-140 (sections/15c-app-statecharts.md, line 140)

- **Main region +1296** (dispatcher 0x7EAF265D, jump table, states 11–168, 131 cases). **13 = `PictBridgeComponent:idle`** (entry 0x7EAFBBA4). Its handler 0x7EAFBF48 maps CustomPrint requests to work states: 13784→30, 13809→31, 13806→32, 13808→36, 13807→37, 13819→38, 13795→58, 13799→62, 13797→65, 13802→66, 13783→84, 13792→136, 13814→137, 13805→138, 13816→139, 13793→140, 13821→141, 13811→142, 13803→143, 13804→157, 13812→158, 13788→166. Play requests: 12261→14, 12264→15, 12267→16, 12262→17, 12274→19. Composite states keep their own sub-state words +1300…+1364. F042's "state 35 at +1300" is inside composite 34 (entry 0x7EAF2F90 GENs 7094 to self).

## 15c-164 (sections/15c-app-statecharts.md, line 164)

| CmpSts_MfAssist 0x7EB7D14B | 0x7EB7D494 (F048) | 11989, 11988, 12014 `evTraReqShtMfScrollThrough`, 12015 `evTraReqShtMfZoomThrough` |

## 15c-166 (sections/15c-app-statecharts.md, line 166)

| CmpCst_Communication 0x7EA9D405 | 0x7EA9D87B | 13161, 13162, 13164–13168 |

## 15c-221 (sections/15c-app-statecharts.md, line 221)

7. **13c §5 "CmpSqp_* vtables have a different layout":** the sequence parts are classes with getInstance + ctor (0x7EA86666 3D, 0x7EA87609 Base, 0x7EA99DB7 Eportrait, 0x7EA9A4E5 MultiExposure, 0x7EA9CA79 Otwb, 0x7EA9CE2F Panorama, 0x7EA9D108 PictBkt). They are plain C++ classes: the base ctor 0x7EA87609 stores vtable 0x7EC550D8 and calls no base ctor and no setActiveContext (V).

