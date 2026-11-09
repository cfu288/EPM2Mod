# Audit A10 batch 3

## 15b-57 (sections/15b-camera-core-index.md, line 57)

| cam_mirror.c | 0x7E642459 | hash 0x7E7B18B8: 1, 2, 5, 6, 9, 10, 145–152 (roles 14b §5) |

## 15b-60 (sections/15b-camera-core-index.md, line 60)

| cam_shutter.c | 0x7E6558AD | hash 0x7E7BBAAC: 5, 6, 7, 11, 12, 145–149 (each → MEC submit 0x7E51787B of an SH request object, or cam timer 0x7E6623CB) |

## 15b-73 (sections/15b-camera-core-index.md, line 73)

| 8 | 0x7E650CCD | COM_GET: copy the current setting block (18 + 9 words, from 0x7E649822) to the caller |

## 15b-94 (sections/15b-camera-core-index.md, line 94)

- Set-list FrameTypes (10, 16, 34–37, 54, 57–59, 62, 63, 65) are a separate number space from frame commands. As frame-command codes, 11 of the 13 values are default slots of 0x7E7AE744; 54 → 0x7E636B40 and 57 → 0x7E636B63 are handled entries (V). (A8 2026-11-09)

## 15b-169 (sections/15b-camera-core-index.md, line 169)

- *ems2 callback* (0x7E670FB8, 0x7E671208, 0x7E67132B, 0x7E671506, 0x7E671683): `movm`, 0 callers, a result decoder 0x7E460DB8/0x7E460FC2/0x7E46118C, then a direct call to the next start. **Chain ends (V):** three callbacks end a chain instead. 0x7E671E92 (loaded by start 0x7E671CC3) decodes (0x7E460DB8, 0x7E46118C) and calls 0x7E672308 (not a start: it runs the analysis 0x7E672896, then calls the user callback *(0x605970F0)). 0x7E6725C6 (loaded by 0x7E67253F) decodes (0x7E460DB8), runs 0x7E672896 and calls *(0x605970F4). 0x7E67287A (loaded by the last start 0x7E67283D; 28 B, `add -4,sp`, no `movm`, no decoder) calls 0x7E460109 and 0x7E4600DC, then *(0x605970F8). The open 0x7E670647 stores these three user callbacks from its argument (+4/+8/+12); the tracking open 0x7E6673A6 passes 0x7E6686D0, 0x7E6689F3 and 0x7E66C1AF. (A9 2026-11-09)

## 15c-94 (sections/15c-app-statecharts.md, line 94)

| 3 Idle (0x7EA7E266) | 11761 → 9 | — |

## 15c-127 (sections/15c-app-statecharts.md, line 127)

| 11 (0x7EB78C84) | if CapIod (+332) vt+12 says active: GEN **5761** to it; else self 12067 | 12067 → 9 |

## 15c-141 (sections/15c-app-statecharts.md, line 141)

- **Region +1280** (0x7EAF1E59): 23 (entry 0x7EAF1E7F GENs **3615** to +1256 = CapPbr) ⇄ 24 on 7079/13791 (`CmpPictBridge Abort Success`).

## 15c-158 (sections/15c-app-statecharts.md, line 158)

- So an owner routes an `evTraReq*` request to the sub-transition whose list holds that id. F049 0x7EB85867 clears the list.

## 15c-170 (sections/15c-app-statecharts.md, line 170)

| Com_ActiveTransitionManagerBufferd 0x7EB8AD37 (vt 0x7EC8C708) | stub `retf` 0x7EB8AE46 | **13361** while the helper is in state 4: the entries of states 7 (0x7EB8B66F, region +316) and 8 (0x7EB8B8EA, region +312) push the static prototype 0x605EF18C (a copy of 13361, built by 0x7EB85D2A from ctor 0x7E96C3D3) onto +144 through 0x7E966C01; the exit code 0x7EB8B458 removes it through 0x7E966CCE. Cab_CameraBase uses it: initRelations 0x7EB893EA sets Cab +276 = facade+128 (the Bufferd member built by 0x7EB8924F), and 0x7EB896CA calls 0x7EB857CA on (+276) (A8 2026-11-09) |

