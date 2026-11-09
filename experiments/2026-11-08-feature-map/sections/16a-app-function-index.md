# 16a — C++ app layer: generated function index (one row per function)

**Scope:** block 0, the C++ app layer **0x7E966A17–0x7EBA7BC0** (Tra / Ope / OlyApi / sdk shell / Cap / Cmp / Com_ / Cab / Dev / Ctg / OXF), as fixed in 13c §1. Round D4 built the index; **round D5 (2026-11-09) fixed the rule-level errors** that the coverage round C6 found (reviews `coverage/round6-review2.md`, `review3.md`), regenerated the TSV and measured it again. It builds on 13c (framework shapes), 14c (protocol shapes), 15c (class index, statecharts) and 13d §6.2 (OlyApi getters).
**Labels:** **V** = verified (read in code or bytes); **I** = inferred (strings, names, callers, a rule).
**Outputs:** `16a-app-function-index.tsv`: 33,089 rows (every `functions.tsv` function in the range with `data_page` = 0 and `suspect` = 0). Columns `addr`, `size`, `role`, `basis` (rule code, §3), `V/I`. The role text is cut at 400 characters (D4: 180).
**Scratch:** `.../scratchpad/d5/app/`: `idx16.py` (the classifier; inputs `ins.pkl`, `vt.pkl`, `apinames.pkl` stay in `d4/app/`), `mktsv.py` (TSV writer), `tiers.py` (specific / partial / context measure), `diff.py` (old/new diff), `whostate.py` (dispatcher cases of a handler), `show.py` (row + disassembly), `old16a.tsv` (the D4 TSV), `chk_changed*.txt`, `final30*.txt` (checked samples with disassembly).

## 1. Area and boundaries

As in D4 (13c §1, 15c class index), with these D4 refinements (V): `sdk` shell 0x7E99A6A8–0x7E99D2B2 and 0x7E9A0254–0x7E9BFA7D; OlyApi second series 0x7E99D2B3–0x7E9A0253; OlyApi first series 0x7E9BFA7E–0x7E9CE116; Ope code (incl. `OlyHfwOpeBlueth` builders) 0x7E9CE117–0x7E9CFDFA; `OlyHfwOpeCustomPrint` interface 0x7E98D2E3–0x7E98FC07; CapCam proper 0x7EA2F2CF–0x7EA2F9E3; `CapPls_PlayState` interface 0x7EA2F9E4–0x7EA3074F.

**D5 split of the 15c row "Cab_CameraBase facade" 0x7EB89214–0x7EB8C264** (it has three reactive ctors). A class's code follows its ctor (I, from the layout of the facade+reactive pairs):

| Range | Class | Basis |
|---|---|---|
| 0x7EB89214–0x7EB8951F | Cab_CameraBase facade (getInstance 0x7EB89214, ctor 0x7EB8924F) | 15c (V) |
| 0x7EB89520–0x7EB8AD36 | `Cab_CameraBase` reactive part (ctor 0x7EB89520, getName "Cab_CameraBase") | getName (V), range (I) |
| 0x7EB8AD37–0x7EB8BCCA | **`Com_ActiveTransitionManagerBufferd`** (ctor 0x7EB8AD37, getName string) | getName (V), range (I) |
| 0x7EB8BCCB–0x7EB8C264 | Com_ event run 7001–7020, 11561–11566 | 13c (V) |

## 2. Inputs (tables the rules use)

Unchanged from D4: the event dictionary (13c / 14c / 15c ids, 1,273 event vtables), the 15c class index (227 class + 271 observer rows), the vtable scan (`vt.py`, 1,875 vtables), class dispatchers (slot 33) and region dispatchers, getInstance list (14c `gi.txt`), the **OlyApi method-name table at RAM 0x602B1F10** (`.data` image 0x7E8E23D0, 969 names, read by 0x7E96E5F0), the `sdk api` table 0x7EBF8188, the `sdk` table 0x7EBF0FA0, the app_check table 0x7EC1C368 and the named-function list. **D5 named functions (V, read this round):**

| Address | Role |
|---|---|
| 0x7E966C01 | pointer collection **add(item)**: count +4, capacity +8, array +12; grows to 2·cap+1 (new[], copy, delete[]) |
| 0x7E966CCE | pointer collection **remove(item)**: overwrites the item with the last one, count−1. fwmap merges the next function (get(i), 0x7E966CFF) after its `retf` |
| 0x7EA18D55 | CapThr **getEntryState()** = RAM 0x602B2E54 (85 callers) |
| 0x7EA1A8A2 | CapThr **setEntryState(id d0)**: writes 0x602B2E54; logs `[CapThr](all)entryState[0x%08x]` when 0x602B2E50 = 1 |
| 0x7E9F72AB | CapImg **pick next play-buffer slot** (vt slot 123 body): 4 × 120-B records at this+1040, slots 1–3; first record with +16 handle = 0, else (this+444)+1, wrapping 4 → 1; then 0x7EA00A7D; returns the slot handle (review F031) |
| 0x7EA00A7D | CapImg **ensure play buffer(handle d0)**: returns a non-zero handle; else `api_play_dummy_Set_PlayMode` and `api_play_Alloc_Playbuf(0)` when mode byte +444 is 0–3 |

## 3. Rules (decision order, first match wins)

The D4 table stays valid (rule codes `named`, `ev-*`, `olyapi-*`, `getInstance`, `obs-*`, `ctor`, `getName`, `dispatcher`, `region-dispatcher`, `guarded-choice`, `sdk-*`, `app_check`, `facade-wrapper`, `reactive-ctor`, `dtor-*`, `state-entry`, `handler`, `initStatechart`, `getter-setter`, `composite-entry`, `member-init`, `cleanUpRelations`, `object-ctor`, `deleting-dtor`, `factory`, `new-event`, `bool-field`, `initRelations`, `transition-step`, `iface-thunk`, `forwarder`, `prologue`, `gen`, `g:*`). **D5 changes** (each one replaces a D4 rule that produced a known error):

| Rule | D4 behaviour (error) | D5 rule (signature) |
|---|---|---|
| `getter-setter` | `clr d0; call X; ret` and `mov K,d0; call X; ret` read as "returns 0 / constant" | a body that holds `call`/`jmp` is never a getter; it falls to `forwarder` and the row shows the argument: "forwarder (d0=0) -> 0xX". New one-instruction shapes: `mov (60xxxxxx),dN; retf` = "getter of RAM global", `mov dN,(60xxxxxx); retf` = "setter of RAM global", `mov (N,a0),d0; ext* d0; retf` = sized getter |
| `forwarder`, `iface-thunk` | the row carried the target's text in "(...)", read as the function's own role | row = own shape + constant args, `this+K`, stores and result constant, e.g. "forwarder (d0=8, stores +312, this+144, a1=0x605EF18C) -> 0x7E966C01", then **"[target role: …]"** = the target row, not this function |
| class prefix | a function without strings took the class of its address range (Ope ranges hold other classes' code) | if the function has no class evidence of its own (strings, `.cpp` tag, vtable slot, ctor, state entry) **and no caller in the range class** (callers seen through plain forwarders; same family = name prefix match), the prefix is **"code in X range, class not proven (callers: …)"**; OlyApi callers are named by method (2,397 rows) |
| `g:transition-action` | small getters and shared helpers whose calls sit in handler branches | not applied to getter shapes or to functions with > 6 distinct callers; a call whose `d0` result is used next (`mov d0,…`, `cmp K,d0`, `btst`, `and`, `or`) is **`g:query`** ("query used in the E branch of handler H (result used)") |
| `handler` state number | only the function that the dispatcher case calls got the state; cases that call a forwarder lost it | dispatcher and region-dispatcher cases are followed through plain forwarders (≤ 4) to the handler; parent chains are walked from the real handler. A parent shows **"parent of states …"**, a handler that is both shows "state 10 (also parent of states 7,8,9)" |
| `handler` vs `null-transition` | a handler whose only branch was −1 + popNullConfig was labelled "null transition" | `handler` (getCurrentEvent) is tested before `null-transition`; the branch shows "(popNullConfig)"; a handler with no parent call shows "no parent fallback (returns 0)" |
| `choice` (new, 34 rows) | choices showed the first 4 target states | popNullConfig + compare chain on a field (`mov N,a1; add a2,a1; mov (a1),d0` or `mov (N,a0),d0`, then `cmp K,d0; bne/beq` blocks that call a state entry): "choice on +572: 28 cases 1->38>39, …; default -> 48" |
| composite targets | the entry inside a composite was reported | a composite entry (`mov K,d0; mov d0,(N,a0); call` with N a state word) is the target; rows print **"K>K2"** = composite K, default sub-state K2 (15c tables list K2, the leaf with the log string) |
| `state-entry` | pushNullConfig entries and split stores were missed | also accepts the two stores split by an address reload (`mov (N,sp),aX`), a first insn window of 14 after a pushNullConfig call (tag "[transient: pushNullConfig first]", 286 rows), and the number in another register (`mov K,a1; mov a1,(S); mov a1,(A)`) when the function calls the Com_ state trace or A is a known active word |
| side effects | `transition-step`, `handler`, exit rows left out notifies and history writes | `transition-step` lists notify / GEN / popNull / via-callee actions; handler branches add "[notify (via 0xX)]"; exits and entries add **"saves +S to history +H"** (load of a state word stored to a non-state field); exits up to 30 insns are accepted when they build no event and do not read the current event |
| `vcalls` | the object offset was taken from the nearest `mov (N,aX),aY` (wrong object) | registers are followed: `calls (aV)` ← `mov (slot,aT),aV` ← `mov (aO),aT` ← `mov (N,aB),aO` or `add N,dR … mov dR,aO`; unresolved objects print `+?` (916 rows changed) |
| content summaries | one callee level, no strings, no arguments | two callee levels (callee ≤ 600 B, its callees ≤ 300 B), callee strings, constant `d0` arguments ("api_user_Set_Touch_Panel_State(d0=0)", "CapThr setEntryState(0x02010201)"), `addObserver`/`removeObserver`, and for call-free functions a **leaf summary** (this-relative fields written, RAM written, `setlb` loop, return constants) |

## 4. Coverage (D4 TSV → D5 TSV, same measure)

`tiers.py` classes each row: **specific** = a table or shape rule gives the role (a forwarder takes the tier of its resolved target); **partial** = generic, but with own strings, api_* calls, events, virtual calls, named callees, leaf summary or handler/entry context; **context** = only callers, a vtable slot or RAM addresses.

| Tier | D4 rows | D5 rows |
|---|---|---|
| specific | 23,279 (70.4 %) | **23,751 (71.8 %)** |
| partial | 7,702 (23.3 %) | 8,726 (26.4 %) |
| context only | 2,108 (6.4 %) | **612 (1.8 %)** |
| blank | 6 | 3 (0x7E976357, 0x7E97F0B1, 0x7E99514A) |

By area (specific / partial / context %): Tra/Ope/OlyApi/sdk 7,002 rows 71 / 26 / 3; Cap 8,647 rows 59 / 38 / 3; Cmp* 14,743 rows 80 / 19 / 0; Com_/Cab 618 rows 74 / 24 / 2; Dev part 1 549 rows 63 / 30 / 6; Ctg 763 rows 83 / 17 / 1; Dev part 2 458 rows 56 / 39 / 5; OXF 309 rows 55 / 41 / 5. Cap interface bodies and Dev part-2 methods moved mostly from context to partial (leaf summaries, callee strings, resolved vcalls); few of them have a specific role.

**Diff D4 → D5 (`diff.py`):** 18,409 rows changed text; **14,621 changed role** when forwarder target text and argument lists are ignored; 858 changed rule code. Main rule-level changes: 1,206 handler rows gained their state number, 707 rows show "parent of states", 87 "null transition" rows are now handlers, 34 choices, 57 rows became state entries, 25 getter rows became forwarders with arguments, 250 RAM-global getters/setters, 102 rows lost "transition action", 25 are queries, 557 rows gained a notify, 17 a history write, 111 show composite targets "K>K2", 99 rows moved to `Com_ActiveTransitionManagerBufferd`, 2,397 rows say "class not proven".

## 5. Measured error rate

**Method (as D4):** draw rows with Python `random.sample` (seed given), dump the disassembly (`show.py`, 45–50 insns), read it, judge the row. **Error** = the row states something false (kind, class, state, slot, event, target, offset). **Weak** = true but generic (counted correct).

| Sample (seed) | Rows | Errors | What was wrong → fix |
|---|---|---|---|
| changed rows (505) | 10 of the 14,621 changed | 0 (2 weak) | — (states 47 / "parent of 5" / "state 10" checked with `whostate.py` and the jump table 0x7EC70994) |
| I (9001), fresh | 30 | **1** (8 weak) | 0x7EA8A0FD "vcalls +32->vt+40": the object is +380, +32 is the argument → `vcalls` register tracking (§3) |
| J (77777), fresh, final rules | 30 | **0** (4 weak) | one text artefact "addObserver to list +None" (0x7EA4440E) and one unrecognised `mov (24,a0),d0; exthu d0; retf` getter (0x7E976A02), both fixed after the sample |

**Result:** 1 error in 60 fresh rows = **1.7 %** (95 % interval about 0.04–8.9 %); the last 30 rows, with the final rules, 0 errors. D4's last measure was 2 / 60 = 3.3 %. All four C6 review errors are fixed by rules, not by hand: 0x7EA1D604 is "forwarder (d0=0) -> 0x7EA1CA98" (Restart_Through), 0x7EA18D55 is getEntryState, 0x7E9E4C43 is "code in OlyHfwOpeSndCtl range, class not proven (callers: OlyApi TouchPanel::endTouchPanel)", 0x7E966CCE is the collection remove. The review-3 state numbers are now in the rows: F042 0x7EAEC172 = CmpEra state 65, F043 0x7EAF235E = PictBridge state 27, F048 0x7EB4E4AD = CmpPRec state 19, F051 0x7EB76DBC = CmpSOve state 29, and the transient entry 0x7EAF21C5 = PictBridge state 27 `backgroundctrl_draw`.

## 6. Reading a row (examples, V)

- `0x7EAD203B CmpERaw_EditRawComponent choice (null transition, popNullConfig) on +572: 28 cases 1->38>39, … 284->60, 341->70, 402->53, 403->65>66, 404->57>58, 405->69, 406->50>51, 407->62>63, 408->54>55, 409->68; default -> 48` (the CmpERaw extra codes of review 3 F041).
- `0x7EB1AB41 CmpPCw_PlayCwComponent state 10 (also parent of states 7,8,9) handler: 11563 … -> state 3 [notify (via 0x7EA7DB63)]; 11562 … -> state 49`.
- `0x7EB8B86A Com_ActiveTransitionManagerBufferd state exit: clears sub-state word +324; first saves +324 to history +328; also pointer-collection remove()` (review 3 F052).
- `0x7EB9CEFF Ctg category 5 transition step: exit (0x7EB9CEF7); notify list +148; … then enter state 13` (F054).
- `0x7EA1C7C5 CapThr_ThroughImage method: CapThr getEntryState(); CapThr setEntryState(0x02010201); [via 0x7EA1D604: (via 0x7EA1CA98(d0=0): api_tft_Restart_Through, …)]` (F033).
- `0x7EB55B34 … vcalls +832->vt+660, +860->vt+292, …` (F050: the +832/+860 play devices).

## 7. Corrections to older sections and reviews

1. **Review round 6 batch 3, F033 and "weakest areas" item (CapThr entry-state ids):** the constants have one more non-zero byte than the review lists. F033 0x7EA1C7C5 writes **0x02010201** (`mov 33620481,d0` at 0x7EA1C7CB), not 0x02010001. The 14 setters 0x7EA1C740…0x7EA1C9D7 set, in address order: 0x02030202, 0x02030201, 0x02010202, 0x02010201, 0x02010102, 0x02010101, 0x01030202, 0x01030201, 0x01030102, 0x01020202, 0x01010202, 0x01010201, 0x01010102, 0x01010101 (V, `mov K,d0` before `call 0x7EA1A8A2`). After the write, the 0x02xxxx01 setters (0x7EA1C76E, 0x7EA1C7C5, 0x7EA1C81C) follow the F033 pattern (Restart_Through(this, 0) through 0x7EA1D604 when this+264 = 1); the 0x02xxxx02 setters call 0x7EA1DF9E and the 0x01xxxx01 setters call 0x7EA1E03E (both reach `[CapThr]exec buffering instruction` 0x7EA1E2BF); the 0x01xxxx02 setters call 0x7EA2010E (event 26853, `execReserveSeqCmd`) (V calls; the meaning of the bytes is I). Other writers of the entry state: 0x7E96F410, 0x7E988079, 0x7E99775A, 0x7EA388B8.
2. **Review 3 F046:** 0x7EB1AB41 is also the **state-10 handler** of CmpPCw, not only the parent of 7/8/9: jump table 0x7EC70994, index 7 → 0x7EB1A9C8 `call 0x7EB1AD88` → forwarder → 0x7EB1AB41 (V).
3. **Review 3 F041 / 15c §4.2:** the review's RAW-only targets 403→65, 404→57, 406→50, 407→62, 408→54 are composite states; their default sub-states are 66, 58, 51, 63, 55. 15c §4.2 lists the leaf state (e.g. 1 → 39); the composite is 38 (V). Every play class's choice is now a row (34 `choice` rows), so the per-class extensions of the §4.2 table can be read from the index.
4. **15c row "Cab_CameraBase facade"** holds three classes; see §1 (Bufferd 0x7EB8AD37–0x7EB8BCCA, I by ctor order). The 15c Bufferd text (state-7/8 entries 0x7EB8B66F/0x7EB8B8EA, exit 0x7EB8B86A) fits that sub-range. Its state-7 entry uses `mov 7,a1; mov a1,(316,a2); mov a1,(172,a2)` (V), which the 13c §3 `mov K,d0` entry signature does not match.
5. **16a D4 rows** for 0x7E966C01 / 0x7E966CCE ("HIGHLEVEL_MAIN / HLS startup method") were range artefacts: they are the generic pointer collection add/remove (§2), used across the app layer (V). **fwmap:** 0x7E966CCE (88 B) includes a second function, the get(i) accessor 0x7E966CFF, after its `retf` (V).
6. **13c §3 shape catalogue:** add the D5 shapes of §3 (choice compare chain; split / register / pushNullConfig-first entries; RAM-global getters; history writes).

## 8. Open questions

1. Cap interface bodies (CapImg, CapPls, CapMed, CapPbr) and Dev part 2: rows are mostly partial (what they call and write), not specific. A slot dictionary per interface (who calls `+K->vt+S` and with which strings) would name them; the resolved `vcalls` offsets (+828 CapDpv, +832/+860 play devices, +200 sequence parts) are the input for it.
2. "code in X range, class not proven" (2,397 rows): many are base-class methods used only by derived classes, or class-family helpers. A sub-range split by string clusters (as for the SndCtl tail, touch-panel Ope code from about 0x7E9E4B3D) would give them a class.
3. The meaning of the CapThr entry-state bytes (0xAABBCCDD: AA ∈ {01, 02}, BB ∈ {01, 02, 03}, CC/DD ∈ {01, 02}) (I: mode / view / sub-mode).
4. OMReactive slots 3, 10, 26, 31, 34 are still unnamed; the class names of the print facade 0x7E991647 and the 30+ "Ope/app class @…" rows of 15c.

## Known rule errors and limits (after D5)

Fixed in D5 (rules, regenerated): `clr d0; call X` read as "returns 0"; range class given without evidence; "transition action" on getters; missing state numbers through forwarders / region dispatchers / pushNullConfig entries; dropped notifies and history writes; forwarders copying the target's text; wrong `vcalls` object offsets. Still open:
- **Handler branches through virtual calls:** a branch that GENs or acts through `(N,a2)->vt+K` shows no action (e.g. 0x7EA62D96, event 5153).
- **Leaf summaries** count only this-relative and absolute-RAM stores; out-parameter writes (`mov d0,(a1)`) and loop sizes are not described (e.g. 0x7EBA1FE5, 0x7EA29150).
- **"class not proven"** is honest but not specific; same-family detection is a name-prefix test, so a family with unrelated names (e.g. "Cap_PlaySlide (slideshow) + CmpShc_ShootingSequenceBase" used by CmpSts_*) is flagged although the code is shared base code.
- **Dispatcher cases** still resolve only `call` targets and plain forwarders; inline cases have no handler row.
- **Constant arguments** show only `d0`; a1/d1 arguments appear only in forwarder rows.
