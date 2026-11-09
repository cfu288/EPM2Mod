# 16a — C++ app layer: generated function index (one row per function)

**Scope:** block 0, the C++ app layer **0x7E966A17–0x7EBA7BC0** (Tra / Ope / OlyApi / sdk shell / Cap / Cmp / Com_ / Cab / Dev / Ctg / OXF), as fixed in 13c §1. This round (D4) answers the coverage finding that the map places every random app-layer function in the right module but gives a specific role to about one in three. It builds on 13c (framework shapes), 14c (protocol shapes), 15c (class index, statecharts) and 13d §6.2 (OlyApi getters).
**Labels:** **V** = verified (read in code or bytes); **I** = inferred (strings, names, callers, a rule).
**Outputs:** `16a-app-function-index.tsv`: 33,089 rows (every `functions.tsv` function in the range with `data_page` = 0 and `suspect` = 0; 8 skipped). Columns `addr`, `size`, `role`, `basis` (rule code, §3), `V/I`.
**Scratch:** `.../scratchpad/d4/app/`: `load.py` (instructions → `ins.pkl`), `vt.py` (vtable starts and slots → `vt.pkl`), `apinames.py` (OlyApi name table → `apinames.pkl`), `idx16.py` (the classifier, ~900 lines), `mktsv.py` (TSV writer), `show.py` (row + disassembly), `verify*.txt` / `verify*_dis.txt` (the checked samples).

## 1. Area and boundaries

The range and its sub-areas are as in 13c §1 and the 15c class index, with these refinements found while building the index (all V):

| Range | Contents | Basis |
|---|---|---|
| 0x7E99A6A8–0x7E99D2B2 and 0x7E9A0254–0x7E9BFA7D | `sdk` debug shell: sub-command handlers (table 0x7EBF0FA0, 28 entries, lowest 0x7E99A7CF), `sdk api` handlers (table 0x7EBF8188) | table words |
| **0x7E99D2B3–0x7E9A0253** | **OlyApi second getter series and its methods** (CameraCommon getter 0x7E99D2DD … SystemCommon `scOsCreateQueue` 0x7E99FAA7; 105 methods carry an API id). 06 §5 treats this as part of the shell | API-id constants (§2.3) |
| 0x7E9BFA7E–**0x7E9CE116** | OlyApi first series: 39 getters + methods; the last method is `TouchPanel::startTouchPanel` 0x7E9CE0B2 (101 B) | API-id constants |
| 0x7E9CE117–0x7E9CFDFA | not OlyApi: Ope code, among it `OlyHfwOpeBlueth::*` request builders 0x7E9CE8C4–0x7E9CF5E6 (they build 13505…13535) | strings |
| 0x7E981245–0x7E98FFAD (15c row "OlyHfwOpeShoot (+PlyMov, BGrCtl)") | string users: `OlyHfwOpePlyMov` 0x7E981663–0x7E981F92, `OlyHfwOpeShoot` 0x7E98235B–0x7E98A70A, `OlyHfwOpeBGrCtl` 0x7E98A854–0x7E98B5A9, and **`OlyHfwOpeCustomPrint` 0x7E98D2E3–0x7E98FC07**: an interface object (ctor 0x7E98D2E3, vtable 0x7EBEE2C4, 36 slots; bodies 0x7E98D2FE–0x7E98FC07) that the print facade ctor 0x7E991647 builds (that ctor also builds EasyPrint 0x7E9927F6) | strings, ctor calls |
| **0x7EA2F2CF–0x7EA2F9E3** | `CapCam_CameraInformation` proper (its dtor 0x7EA2F894, helpers 0x7EA2F9D3/0x7EA2F9D9) | ctor/dtor, vtables |
| **0x7EA2F9E4–0x7EA3074F** | **`CapPls_PlayState` interface**, not CapCam: ctor 0x7EA2F9E4 (only caller: the CapPls facade ctor 0x7EA27EF9) stores vtable **0x7EC3760C** (215 slots, the +860 interface of 14c §2.6); 214 of its slot targets sit at 0x7EA2F9F2–0x7EA30731; dtor body 0x7EA2F9F5 + clean-up 0x7EA30745 | vtable slots, ctor caller |

## 2. Inputs (tables the rules use)

| Table | Source | Size | Gives |
|---|---|---|---|
| Event dictionary | 13c-event-ids.tsv + 14c-event-ids-extra.tsv names + 15c-event-id-fixes.tsv owners + the named ids of 13c/14c/15c | 1,273 vtables | ctor / isTypeOf / 18 vtable slots per id; id names |
| Class index | 15c-class-index.tsv | 227 class rows + 271 observer rows | class by address range; ctors, getInstances, observer ctor/vtable/event |
| Vtables | `vt.py`: every `mov VT,dN; mov dN,(aM)` with VT in 0x7EBC0000–0x7EC93000, slot run = consecutive code words | 1,875 vtables, 9,279 slot targets | "slot K of class X"; vtable owner = the ctor that stores it, or the class-index ctor that calls the storing function |
| Dispatchers | slot 33 (vt+132) of every class vtable, parsed as compare chain or jump table (15c `sc.py` logic) + shape scan for region dispatchers | 165 + 41 | handler → (class, state) map, parent chains |
| State words | the (sub, active) offsets written by state entries of each class | — | "state exit" and "composite entry" tests |
| getInstances | 14c `gi.txt` | 139 | RAM slot, interface offset |
| **OlyApi method names** | **RAM 0x602B1F10 = `.data` image 0x7E8E23D0** (14d: RAM + 0x1E6304C0): 6 group pointers → 63 class arrays → method-name pointers; read by 0x7E96E5F0 (id 0xGGCCMM → name) | 969 names | "OlyApi Class::method (API id)" for every method that loads its id and calls 0x7E96E5F0 |
| OlyApi getters | 13d §6.2 (39 + 5) | 44 | "OlyApiX getInstance" |
| `sdk api` table | 0x7EBF8188, 635 × {handler, code, name} (06 §5) | 631 handler rows | "sdk api handler M72 cancelRecview" |
| `sdk` sub-commands / app_check | 0x7EBF0FA0 {name, fn} / 0x7EC1C368 (119 words, 14c §1) | 28 / 116 | command name / table index |
| Named functions | OXF runtime (13c §2), Com_ framework (13c §6), EVFW/HLS (14c §2.4), play-base helpers (15c §3) | 147 | fixed names |
| api_* wrappers | functions in 0x7E675E00–0x7E690000 whose own string starts `api_` | — | callee names in role texts |

The OlyApi name table is new (V): 0x010129 = `CameraCommon::ctrlLcdBacklight` (review F035's "CameraCommon method 0x29"), 0x050421 = `Bluetooth::showReceiveImage` (F031), 0x02010B = `Shooting::stopHistogram`. The low byte of each id is the 1-based method index into the class array.

## 3. Rules (decision order, first match wins)

Each rule reads the instruction list of the function (`functions.txt`). The class prefix of a role is the 15c class-index row containing the address, except for slot bodies of a vtable that lies in another row and is used by no other owner (the CapPls interface, the CustomPrint interface): those take the vtable owner. Codes are the TSV `basis` column; counts are rows.

| Code (rows) | Signature (instructions) | Role text |
|---|---|---|
| `named` (147) | address in the named-function list | fixed name |
| `omreactive-slot` (17) | OXF function in a slot of the OMReactive base vtable 0x7EC91FE8 | "OMReactive base vtable slot K" |
| `ev-ctor` / `ev-isTypeOf` / `ev-vtslot` (1,015 / 1,199 / 1,273) | address = ctor / isTypeOf / a slot of an event vtable (13c §3 byte shapes; dtor = slot 0 `call 0x7EBA490C; mov 0,a0; ret`) | "event 12067 evTraCmp_NextState ctor (vt, parent, owner)" |
| `olyapi-getter`, `getInstance` (44, 139) | getter tables | class, RAM slot, interface offset |
| `obs-ctor`, `obs-update` (271, 263) | 15c observer row ctor; slot 0 of its vtable (75-B GEN shape, or notify 0x7EB86ED0 = relaying observer) | "observer update(): builds 7605 and GENs it to target +20" |
| `ctor` (316) | 15c class-index ctor | "X ctor (stores vt …)" |
| `getName` (74) | slot 36 of a class vtable **and** calls OMString ctor 0x7EBA6F2B | "X getName() = "X"" |
| `dispatcher` (165) / `region-dispatcher` (41) | slot 33 / `mov (A,a0),dN` in the first 6 insns + compare chain or jump table whose cases call handlers | "rootState_dispatchEvent on +212: N states (…)" |
| `guarded-choice` (2) | ≥2 `call G; cmp 1|0,d0; bne|beq` blocks, no getCurrentEvent, calls state entries | "condition connector → states …" (F039) |
| `sdk-cmd`, `sdk-api`, `app_check` (28, 631, 116) | table entry | command / table index |
| `olyapi-method` (601) | `mov 0xGGCCMM,d0` (first 14 insns) + call 0x7E96E5F0 | "OlyApi Shooting::getRecViewInfo (API id 0x020111)" |
| `facade-wrapper` (82) | two calls to setActiveContext 0x7EBA675E, ≤40 B | "setActiveContext(this) and (this+K)" (15c §2) |
| `reactive-ctor` (5), `dtor-slot0` (165) | vtable store + 0x7EBA675E / slot 0 of a non-event vtable (or the body after a slot-0 prologue) + own vtable store | ctor / dtor |
| `state-entry` (2,407) | `mov K,d0; mov d0,(SUB,a0); mov d0,(ACT,a0)` in the first 7 insns (bytes `80 KK fa 10 SS SS fa 10 AA AA`, 13c §3), no vtable store before it | "X state K entry (+SUB/+ACT): actions" |
| `null-transition` (206) | calls popNullConfig 0x7EBA6695 or pushNullConfig 0x7EBA66B3 | null transition / transient entry → states |
| `handler` (2,586) | calls getCurrentEvent (0x7EBA6D64 or vt+60), then `mov ID,d0; mov (8,a1),a1; calls (a1)` tests | "X state N handler: ID → state K (builds E); …; else parent P"; N from the dispatcher map, "parent (fallback)" when reached as a parent; `[timeout handler]` when it tests −2 |
| `initStatechart` (175) | `clr d0` + only `mov d0,(N,a0)` + `retf` | zero N state words |
| `getter-setter` (3,151) | 1–2 insns + `retf`: `mov (N,a0),d0`, `mov d0/a1,(N,a0)`, `add K,a0` (interface this-adjust), constants, empty `retf`; **`clr d0; mov d0,(N,a0); retf` with N a state word = "state exit: clears sub-state word +N"** | getter/setter/exit |
| `composite-entry` (1,151) | `mov K,d0; mov d0,(N,a0)` with N a state word, then a call (often the entry of the default sub-state) | "state K entry (composite: sub-state word +N = K) then enters state K'" |
| `dtor-body` (146) | `mov VT,d0; mov d0,(a0)`; call; `mov 0,a0; ret` | dtor body |
| `member-init`, `cleanUpRelations` (2, 200) | `add N,a0; clr d0; stores` / null-if-set field runs with no calls (review F042 shape) | zero-init / nulls relation pointers |
| `object-ctor` (239) | vtable store at (this) within the first 4 insns, optional base-ctor call before it | object ctor (Com_ observer member class when the base chain reaches 0x7EB85D67) |
| `deleting-dtor`, `factory`, `new-event`, `dtor-base` (26, 29, 31, 72) | null check + dtor + operator delete; new + ctor; new + event ctor without send; calls 0x7EBA63DD/0x7EB8705F | as named |
| `bool-field` (5), `initRelations` (113), `transition-step` (87) | compare-and-return-0/1 on a field; ≥2 setter/setTarget calls (14c §3); ≤48 B calling an exit and an entry | as named |
| `iface-thunk` (1,293), `forwarder` (4,905), `prologue` (1,656) | `mov (4|8|52,a0),a0` + one call (≤12 insns) / only moves + one call / only `movm` + `add -N,sp` | role of the target (or of the body that follows), appended as "-> 0xT (role)" |
| `gen` (466) | event ctor + 0x7EBA4C8D (or 0x7EB871B1), ≤200 B | "sends E to self / +off / EVFW router / via interface slot 7"; the target is the last writer of the register passed to vt+4 / vt+28 |
| `g:transition-action` (561), `g:entry-action` (218), `g:state-exit` (90), `g:condition` (12), `g:guard` (3) | no shape rule; called from an isTypeOf branch of a handler of the same class / from a state entry / clears a state word after exiting the active sub-state / bool without calls in a branch / tested with `cmp 1,d0` | context + content summary |
| `g:str`, `g:api`, `g:vcall`, `g:vtword`, `g:callers` (2,038 / 345 / 892 / 790 / 2,492) | nothing above | own strings, api_* callees, events built, virtual calls `+field->vt+slot`, RAM globals, vtable slot, best-described caller |

Content summaries (entries, actions, generic rows) list, in order: events built, `GEN to …`, notify of list +N, api_* callees, popNull/pushNull, request-registry calls, state trace, `schedule timeout N ms`, the same for one level of small callees as `[via 0xX: …]`, then the first meaningful own string.

## 4. Coverage

| Tier | Rows | Share |
|---|---|---|
| T1: a table or shape rule names class + slot / state / event / API name | 25,553 | **77.2 %** |
| T2: generic, but with own string, api_* calls, events, virtual calls, RAM, or handler/entry/exit context | 5,312 | 16.1 % |
| T3: generic, only callers and/or a vtable slot | 2,218 | 6.7 % |
| blank (nothing applies) | 6 | 0.02 % |

By area (T1 / T2 / T3 %): Tra/Ope/OlyApi/sdk 7,002 rows 74 / 18 / 8; Cap 8,647 rows 70 / 19 / 10; CmpSts/CmpSqp/Cmp 14,743 rows 84 / 13 / 4; Com_/Cab 618 rows 76 / 16 / 9; Dev part 1 549 rows 69 / 23 / 7; Ctg 763 rows 86 / 8 / 6; Dev part 2 458 rows 58 / 24 / 18; OXF 309 rows 61 / 27 / 12. The weakest rows are mid-size Cap and Dev part 2 methods without strings (feature logic reached only through interface thunks).

## 5. Measured error rate

**Method.** Draw 30 rows at random from the index (Python `random.sample`, seed given), dump each function's disassembly (`show.py`), read it, and judge the role. **Error** = the row states something false: wrong kind (dtor called forwarder, exit called action), wrong class, state, slot, event or target. **Weak** = true but generic (counted as correct). After each sample the rules were fixed and the index rebuilt; the next sample is new rows.

| Sample (seed) | Errors | What was wrong → fix |
|---|---|---|
| A (11) | 5/30 | three composite entries (`mov K,d0; mov d0,(872,a0); call`) labelled forwarders; a dtor (`mov VT,d0; mov d0,(a0); call; mov 0,a0`) labelled forwarder; GEN target "+0" for a send to the EVFW router → `composite-entry`, `dtor-body`, router test |
| B (12) | 0/30 | (4 weak) |
| C (2026) | 1/30 | OMReactive slot 17 0x7EBA653C called "deleting dtor" → `omreactive-slot`, deleting-dtor only at slot 0 |
| D (77) | 2/30 | factory size read from a vtable constant; observer-class ctor (base ctor + vtable store) labelled forwarder → `object-ctor` before `factory` |
| E (99) | 2/30 | GEN target taken from a sub-call ("self" instead of +332, interface slot 7); `OlyHfwOpeBlueth` code labelled OlyApi → register-writer tracking, `[via …]` tags, OlyApi range ends 0x7E9CE116 |
| F (4242) | 3/30 | getName claimed for an interface thunk in slot 36; a dtor labelled ctor; a state exit labelled transition action → getName needs 0x7EBA6F2B, `mov 0,a0; ret` = dtor, `is_exit` |
| G (31337) | 1/30 | "clean-up step" claimed for a predicate called by a dtor → wording "called only by dtor" |
| H (555) | 1/30 | a bool condition labelled transition action → `g:condition` |

**Result:** 15 errors in 240 checked rows overall (6.3 %), falling to **2 / 60 = 3.3 % on the last two samples** (G + H, rules final except for the two one-line fixes they caused). With 60 rows the 95 % interval is roughly 0.4–11.5 %, so "< 5 %" is the point estimate, not a bound. All 15 errors were in role kind or target, except the class prefix of sample E (OlyApi/Ope). Sample H also showed the coarse prefix "Tra event run" on a non-event function (judged weak; prefixes now come from the class row). Weak rows (true but generic) were 3–6 per 30, all in tiers T2/T3.

**Known limits (I):** a forwarder's text is its target's role, so a forwarder that also stores a field may be described only by its call; dispatcher cases resolve only `call` targets (inline handlers show as cases without a handler row); `handler` target states come from the first state-entry reached through ≤3 small calls, so a branch that enters through a large helper shows no "→ state".

## 6. Reading a row (examples, V)

- `0x7EB78A88 … CmpSdw_ShutdownComponent state 8 handler: 3344 … -> state 11; else parent 0x7EB786C5` (15c §4.4).
- `0x7EAFBF48 … Cmp_PictBridgeComponent handler: 13801 (builds 3613); 13792 -> state 136; …` (15c §4.5 idle handler).
- `0x7EAF265D … region/sub-state dispatcher on +1296: 131 states` (PictBridge main region).
- `0x7EA3021B … CapPls_PlayState interface … thunk (this+4) -> 0x7EA2B2B9 … [vt slot 134 …]` (review F044 is CapPls interface slot 134).
- `0x7E9CBB83 OlyApi Shooting::getRecViewInfo (API id 0x020111); vt word 0x7EC0F510`.
- `0x7EA4BAE1 self-timer capability transition action on 24413 (in handler 0x7EA4C485 state 11)`.

## 7. Corrections to older sections

1. **15c-class-index row `CapCam_CameraInformation` 0x7EA2F2CF–0x7EA3074F** holds two classes: CapCam 0x7EA2F2CF–0x7EA2F9E3 and the **CapPls_PlayState interface 0x7EA2F9E4–0x7EA3074F** (§1; V: vtable 0x7EC3760C slot words, ctor 0x7EA2F9E4 ← 0x7EA27EF9).
2. **13c §5.1** "F044 (0x7EA2B2B9) is called from 0x7EA2FC7E, which is in CapCam": the only caller is **0x7EA3021B** (site 0x7EA30221), the CapPls interface thunk for **slot 134**; 0x7EA2FC7E is the slot-47 thunk (→ 0x7EA29226). Both are CapPls interface code (V).
3. **13d §6.2 / 06 §5:** every OlyApi method name is in the table at RAM 0x602B1F10 (`.data` image 0x7E8E23D0); 0x7E96E5F0 maps id 0xGGCCMM → name (§2). The `sdk` shell is two pieces around the second OlyApi series 0x7E99D2B3–0x7E9A0253, and the first OlyApi series ends at 0x7E9CE116 (§1) (V).
4. **15c row "OlyHfwOpeShoot (+PlyMov, BGrCtl)"** also holds the `OlyHfwOpeCustomPrint` interface 0x7E98D2E3–0x7E98FC07 of the print facade 0x7E991647 (§1) (V strings and ctor call; the class name of 0x7E991647 is I).
5. **13c §2 open question 2 (OMReactive slots):** slot 17 (vt+68) = **0x7EBA653C**; 238 vtable words point to it (every reactive class inherits it). For a non-NULL argument it calls 0x7EBA4E2D (event `setDestination(NULL)` through 0x7EBA499C, then +28 = 1), then 0x7EBA4DE4, which restores the **timeout-event vtable 0x7EC91B14** (13c §2), and frees the event through the returned pointer or operator delete 0x7EBA62EB (V calls). Role: Rhapsody `cancelTimeout` (I).
6. **13c §3 shape catalogue, additions (V shapes, counts from this index):** state exit `clr d0; mov d0,(N,a0); retf` with N a sub-state word (1,088 rows, plus 90 exits that first exit the active sub-state); composite entry `mov K,d0; mov d0,(N,a0); call default-sub-state-entry` (1,151); transition step (exit + enter, ≤48 B, 87); bool condition inside a handler branch (12). 13c's "2,879 state entries" counts both entry forms; this index finds 2,407 two-word entries + 1,151 composite entries.
7. **Observer vtables (15c §2):** slot 7 of an observer vtable can be the observer-class dtor: vt 0x7EC3FA54 slot 7 → prologue 0x7EA4ACFA → 0x7EA4ACFF (restores the vtable, clean-up 0x7EA4AD74, then the Com_ observer dtor 0x7EB85D75) (V for this one; I as a rule).

## 8. Open questions

1. 2,218 T3 rows (only callers / vtable slot): mostly Cap interface bodies and Dev part 2 methods without strings; naming them needs the slot meaning per interface (14c §2.6 has only the most used CapPls/CapImg slots).
2. The class name of the print facade 0x7E991647 (CustomPrint + EasyPrint) and of the 30+ unnamed "Ope/app class @…" rows of 15c.
3. OMReactive slots 3, 10, 26, 31, 34 are still unnamed (slot 17 is now placed, §7 item 5).
4. `handler` rows whose branches enter states through large helpers have no target state; a deeper entry search (with a size limit per level) would fill them.

## Known rule errors found by coverage round C6 (2026-11-09)

Rows fixed in the TSV: 0x7EA1D604, 0x7EA18D55, 0x7E9E4C43 and 0x7E966CCE. The rules behind them are not yet rerun, so expect more rows of the same kinds:
- **Getter-setter rule:** it reads `clr d0; call X` as "returns 0". It is a call with argument 0.
- **Class from address range:** a function without strings inside a class range is given that class. Ope ranges hold code of other classes (TouchPanel code inside OlyHfwOpeSndCtl).
- **"Transition action" rule:** it labels small getters whose only use is inside handlers.
- **Missing state numbers:** handlers reached through forwarders or region dispatchers, and entries that start with pushNullConfig, often lack their state number.
- **Missing side effects:** shape-labelled rows leave out side effects, such as observer notifies and history-field writes.
