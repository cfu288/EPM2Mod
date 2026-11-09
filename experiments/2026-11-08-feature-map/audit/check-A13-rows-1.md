# Check A13, batch 1: 25 random index rows (5 per index)

Independent read of each function in block 0 (runtime = 0x7E421020 + offset), with `tools/fwmap.py fn/xref`, `tools/disasm.py` and raw word dumps. Verdicts: CORRECT / THIN / MINOR / WRONG / UNCHECKABLE (rubric in the brief).

| index | addr | V/I | verdict | what is false / what it really does | evidence |
|---|---|---|---|---|---|
| 16a | 0x7EA6C622 | V | **MINOR** | Prologue (`add -4,sp`), vt slot 0, range and forwarder are all true. The quoted target role is false. 0x7E966BD6 is not an "EyeFi/FlashAir mode info" dtor. It is the dtor of the generic **pointer collection** (count +4, cap +8, array +12; it frees +12 through 0x7EBA62F3 and zeroes +4/+8/+12). It has 36 callers across the app. The class name comes from the address range. | vt 0x7EC4810C is loaded by code at 0x7EA6C5E8, word 0 = 0x7EA6C622; body 0x7EA6C625 = `add 12,a0; call 0x7E966BD6; mov 0,a0; ret`. vt 0x7EBCDAC0: slot 1 = 0x7E966CFF (the map's own "pointer collection get(i)"); 0x7E966BD6 stores 0x7EBCDAC0 and frees (+12). Callers of the body: 0x7EA78385 (CmpSts_RecordController range 0x7EA7822A–0x7EA79CE1) and 0x7EBA587C (OXF) |
| 16a | 0x7EB2796E | V | CORRECT | true: CmpPEvc parent handler. On getCurrentEvent()->vt+8(12067) it clears sub-state +924 (0x7EB27966) and enters state 49 (0x7EB2838B → 0x7EB28393: +872/+212 = 49, "Cmp_Play%s Idle"). It returns 1, else parent 0x7EB2511F | dispatcher 0x7EB2496A: table 0x7EC743A4, case 37 = 0x7EC7442C → 0x7EB24A9D → `call 0x7EB27A99`. 0x7EB27A99 falls back to 0x7EB2796E at 0x7EB27C2B |
| 16a | 0x7E97A359 | V | THIN | true (`movm [d2]; add -4,sp` prologue of 0x7E97A35E; slot 1 of vt 0x7EBE3940; callers 0x7E9798AA, 0x7E97A713). The row gives only context. The body is a bool query isMediaAccess(type d0): for type 4 it tests flag this+32, for type 32 it tests this+36, and it ORs in the global state from 0x7E974A85 (RAM 0x602B1FA8/0x602B1FB4) | ctor at 0x7E97A2F4 stores vt 0x7EBE3940 at this+0; 0x7EBE3940 = 0x7E97A32B, 0x7EBE3944 = 0x7E97A359 |
| 16a | 0x7E9A03F3 | I | THIN | every listed call is true. The shape is a dtor-like body: member at +8 → 0x7E9A053F → 0x7E975CD3 (returns 0), then 0x7E9E5737 removes this from the container at this+4 (0x7E9E5A46: lock, pointer-collection remove 0x7E966CCE from list +36, unlock) | ctor at 0x7E9A03C8 stores vt 0x7EBF553C; word 0x7EBF5550 = slot 5 |
| 16a | 0x7EB2A250 | V | CORRECT | true: one-call forwarder to the state-17 entry 0x7EB2A258 (+884/+212 = 17, "is_reserve_print start", builds 12067). Its only caller 0x7EB2A1FB sets +872 = 16 first | 0x7EB2A258: `mov 17,d0; mov d0,(884,a3); mov d0,(212,a3)`; 0x7EB0EC7E = `clr d0; mov 5636,d1; mov a1,a0; call 0x7E5082B6` |
| 16b | 0x7ED24D23 | V | CORRECT | true: the panel-base selectLayout(i). It calls 0x7ECEF4E0 (copies rect i, 0..3, of the table at +64 into +8..+14), then calls vt+252 on every child, then 0x7ED2307B on the +768 list and on the app-window list. It returns 1 on every path | 116 aligned words point here (115 more), e.g. 0x7EF11624 |
| 16b | 0x7EDEB068 | V | CORRECT | true: page 329 (OlyApiEditColor) key slot. Key 2 (LEFT) / 5 (MENU) → 1, key 4 (OK) → 2, else 0, then it calls 0x7EDEB1FD | vt 0x7EFFDF1C: slot 3 = word 0x7EFFDF28 = 0x7EDEB068; 15a tsv page 329 |
| 16b | 0x7ED71155 | I | THIN | true (in panel 29 range 0x7ED6F769–0x7ED71D09; only caller 0x7ED70C5E, which calls moveTo 0x7EDC18C8, setVisible 0x7EDC1851, setListIndex 0x7EDC1875). Own role not given: a leaf that sets 4 out-flags from byte d0: (d0 mod 5 == 1) → *a1, (d0 mod 5 == 0) → *d1, 0 < d0 < 4 → *(sp+20), 30 < d0 < 36 → *(sp+24) | disassembly |
| 16b | 0x7ED497B1 | V | CORRECT | true: panel 108 vt 0x7EF33B24 + 400 = word 0x7EF33CB4. For each of blocks 0, 4, 5, 77, 6 it tests dirty (0x7ECEFCE6) and calls DM get 0x7ECEF64F (into +984/+912/+944/+976/+964), then a per-block redraw helper | disassembly; 15a tsv panel 108 |
| 16b | 0x7ED810C3 | I | THIN | true (panel 9 range 0x7ED8047E–0x7ED82024; callers 0x7ED805E9, 0x7ED808DD, 0x7ED81F45; setVisible(0) on +1076/+1080). Only mechanics: it branches on mode byte +1271 (1–4) and on 0x7EDC604D() == 28 / byte +1446, then calls 0x7ED8113A(0/1) and 0x7ED8177C | disassembly |
| 16c | 0x7E5CA752 | V | CORRECT | true. It splits the new path (0x7E5C88EF), builds a FILE on the stack (+452 op mask = 1, +456 → name), and walks the old path (0x7E5C9470). The callback 0x7E5C920F tests `btst 1` and calls 0x7E5B604F, which memcpy's the 11-B name into both entry copies (FAT) or writes the exFAT hash/length. It returns 0 / -1 | the callback address 0x7E5C920F is stored at +20 in 0x7E5C9470; 0x7E500D33 = memcpy(a0 dst, a1 src, d0 n) |
| 16c | 0x7E550927 | V | CORRECT | true (`mov 211,d0; retf`; the only caller 0x7E57A140 reads it as a threshold in a ratio band check next to 191/284/355). "under 0x7E55FFA3" names 1 of the 3 callers of 0x7E57A140 | disassembly |
| 16c | 0x7E5853A1 | V | THIN | every statement is true (0x25000702, prm 0x8551/0x8D21, codes to 0x7E585A9C). The row misses the role: this is the TakeExp **command switch** (byte 1 must be 1; cmd byte 1..52 → jump table 0x7E791578; error log on bad input). The code list also misses 0x507 (0x7E58546D) | disassembly |
| 16c | 0x7E50F101 | V | THIN | true: a setlb loop of 18 that sets u8 pairs 0x604F3F7C + 2i and +1 to 1 (36 bytes). Only caller 0x7E50D7CD ← 0x7E503DD4 | disassembly |
| 16c | 0x7E5A5EF5 | V | THIN | true call graph only (caller 0x7E5A605B ← 0x7E5A2A6F). It fills two IMG job blocks (0x7E5A0EB6 with 7202/196 and 7203/104) from 4 coordinate words at +1176 and from fields +16516/+16896/+16898 | disassembly |
| 16d | 0x7E91D925 | I | CORRECT | true: returns (head(+232).next != &head), so 1 when the list is not empty. Both callers use d0. "tx packet" is a hedged name: the nodes carry a CID at +26 (0x7E91D936), and on disconnect they are drained to 0x7E921667(17) | disassembly |
| 16d | 0x7E68029F | V | THIN | true: case key 0x50001 (= class 0x60000 − 0xFFFF) in table 0x7E7C94E0 → 0x7E67F45A → 0x7E67F49F. 1 of 3 callers (also 0x7E998001, 0x7E998A7B). Own role: builds u16 {1,1,0,0,0,0} on the stack, calls 0x7E457F63, passes its u16 to 0x7E68CF52, returns 0 | disassembly |
| 16d | 0x7E7071EF | I | CORRECT | true: count = (+12)/(+14); it searches the u32 gui[] at +8 for d0 and returns the index, or 0 when not found or gui = NULL | disassembly; 13e record layout |
| 16d | 0x7E67DD54 | V | THIN | true (0x7E9D6160 calls it directly; 0x7E67DDCA → 0x7E67DAAB → here = 2 levels). 1 of 6 callers. Own role: for request classes 0x2000000/0x2010000/0x2020000/0x2030000/0x4060000 it scans the 75 × 8-B table at RAM 0x6059FF7C and returns 0 if the request is excluded, else d0 | disassembly |
| 16d | 0x7F0933B0 | V | THIN | true (0x7F089208 → 0x7F0894D8 → here). Own role: if u16 [0xA06E034C] == 1, clear it and call 0x7F08FA37 | disassembly |
| 16e | 0x7EE36B89 | V | CORRECT | true: the MT loader (table 0x7F027C4C entry 2, magic "MT" at 0x7F02800F) calls it. It reads 3 arrays (count via stream vt+4, allocate 0x7EE36EDD, fill 0x7EE364CF/0x7EE36432/0x7EE363D9) and checks them (0x7EE36377: first time 0, strictly ascending, last ≤ duration). "up to 3" is loose: all 3 are always required | disassembly |
| 16e | 0x7EE83BAC | V | THIN | true: calls 0x7EE83AF0 (stream slot +0 reads a byte into +128, slot +12 reads 3 bytes into +129) and returns (d0 == 1). Only caller 0x7EE83901 | disassembly |
| 16e | 0x7EEC3A8B | V | THIN | true: ctor/dtor code at 0x7EEC3141/0x7EEC3152 loads vt 0x7F031B54. Slot 29 = 0x7EEC3A86 (movm prologue of this body); 0x7EEC3D55 = slot 32 (calls it when +120 bits = 3); 0x7EEC40A3 = body of slot 45 (0x7EEC409E). Mechanics only | word dump of 0x7F031B54.. |
| 16e | 0x7EE74066 | V | THIN | true for the null path only (0x7EE62AD7(1,2) when no error is set). The main path is not stated: it stores d0/d1 at +76/+80, calls 0x7EE7384A and returns 1. "under 0x7EE72CE6 (2 levels up)" is true | disassembly |
| 16e | 0x7EE8541F | V | THIN | true. It is the fini body of class 49: it calls 0x7EE7F976, then string fini 0x7EE7F27B on +136 and +160, then 0x7EE8D3BF. 0x7EE8556F only wraps it | disassembly |

## Counts

| index | V rows | I rows |
|---|---|---|
| 16a | 2 CORRECT, 1 THIN, 1 MINOR | 1 THIN |
| 16b | 3 CORRECT | 2 THIN |
| 16c | 2 CORRECT, 3 THIN | — |
| 16d | 3 THIN | 2 CORRECT |
| 16e | 1 CORRECT, 4 THIN | — |
| all | 8 CORRECT, 11 THIN, 1 MINOR, 0 WRONG | 2 CORRECT, 3 THIN |

## Notes

- **MINOR 0x7EA6C622 (16a):** the copied target role "EyeFi/FlashAir mode info iface/member dtor (vt 0x7EBCDAC0)" is a class taken from the address range. Rows 0x7E966BD1 and 0x7E966BD6 carry the same name. vt 0x7EBCDAC0 is the pointer collection (the map's own row 0x7E966CCE names its slots 1 and 2 as get(i) etc.). Those two rows, and every "[target role: …]" that copies them, need "pointer collection dtor".
- THIN pattern: 16d and 16e "under X (N levels up)" rows, and 16c call-graph rows, name 1 of several callers and give no own role, even where the code is short and clear (0x7E67DD54, 0x7F0933B0, 0x7E68029F).
- 0x7E5853A1: the 16c row does not say that this is the TakeExp command switch, although the row of 0x7E586462 already names the switch.
