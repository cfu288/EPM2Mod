# 16a — C++ app layer: generated function index (one row per function)

**Scope:** block 0, the C++ app layer **0x7E966A17–0x7EBA7BC0** (Tra / Ope / OlyApi / sdk shell / Cap / Cmp / Com_ / Cab / Dev / Ctg / OXF), as fixed in 13c §1. Round D4 built the index; round D5 fixed the C6 rule errors. **Round D6 (cycle 2, 2026-11-09) is about precision:** it fixed the rule errors named by audit A12 (`audit/check-A12-rows-1.md`) and coverage C7 (`coverage/round7-review2.md`, `review3.md`), measured the precision of every rule with more than 50 rows, fixed or demoted each rule with a wrong row, and regenerated the TSV. **Round D7 (cycle 3, 2026-11-09) turns context-only rows into specific roles without losing precision:** it fixed the rule errors named by coverage C8 (`coverage/round8-review2.md`, `review3.md`) and audit A13 (`audit/check-A13-rows-1.md`, `-2.md`), added five rules (`body`, `own-name`, `dtor-noreset`, handler guards / shared code, entry switches), added 10 hand roles, re-measured every new or changed rule (§5.1) and regenerated the TSV (§3.2). It builds on 13c (framework shapes), 14c (protocol shapes), 15c (class index, statecharts) and 13d §6.2 (OlyApi getters).
**Labels:** **V** = the rule read the bytes and its samples (§5) found no wrong row after the last fix; **I** = inferred, or a rule that was demoted (hedged with "probably").
**Outputs:** `16a-app-function-index.tsv`: 33,089 rows (every `functions.tsv` function in the range with `data_page` = 0 and `suspect` = 0). Columns `addr`, `size`, `role`, `basis` (rule code, §3), `V/I`: **26,617 V, 6,472 I** (D6: 25,286 V, 7,803 I). The role text is cut at 400 characters.
**Scratch D7:** `.../scratchpad/d7/app/`: `idx16.py` + `mktsv.py` (builder, D7 rules), `tiers.py`, `diff7.py`, `samp7.py`/`samp8.py` (seeded pool samples), `samp.py` (final sample); samples `s1_1-4.txt` (round 1, 148 rows), `s2_1-3.txt` (round 2), `fin40.txt` (final), `CHECK-BRIEF.md` (rubric with the D7 notation); `base.tsv` = the D6 TSV rebuilt (identical to the D6 section TSV), `final.tsv` = this TSV. **Scratch D6:** `.../scratchpad/d6/app/`: `idx16.py` (classifier; inputs `ins.pkl`, `vt.pkl`, `apinames.pkl` stay in `d4/app/`), `mktsv.py` (TSV writer, header, demotions), `tiers.py`, `diff6.py`, `samp.py` (seeded rule samples), `show.py`; check samples `chk1-5.txt` (round 1), `rchk1-3.txt` (round 2), `r3a/r3b.txt` (round 3), `fin40a/b.txt` (final), `CHECK-BRIEF.md` (the checkers' rubric); `c7_16a.tsv` = the TSV before D6.

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
| 0x7EA7D270 | **D7:** CM **all-started check** (14c §2.2 step 6): returns 1 only when 0x7EA7D3F6 (walks collection +256; 0 when an item has +168 ≠ 4) and 0x7EA7D2A8 (walks collection +240, calls each item vt+12) both return non-zero (92 callers: the state-7 handlers of every CM copy) |
| 0x7EA7D28D | **D7:** CM **all-stopped check**: returns 1 only when 0x7EA7D496 (walks +292; 0 when an item has +168 ≠ 3) and 0x7EA7D378 (walks +276, item vt+12) both return non-zero (the state-6 handlers) |
| vt 0x7EBCDAC0 | **D7:** the **pointer collection** vtable (slot 0 dtor 0x7E966BD1 → 0x7E966BD6: frees +12 with delete[], zeroes +4/+8/+12, returns a0 = 0; slot 1 = get(i) 0x7E966CFF); stored by 36 container ctors that build a collection inline (A13-1) |

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

### 3.1 D6 changes (each replaces a rule that wrote a false row)

| Rule / part | Error found (source) | D6 rule |
|---|---|---|
| `sdk-api` table | read one field late: every handler had the next entry's command (C7-2 item 2) | table 0x7EBF8180, `{cmd*, name*, handler*}`, 636 entries, 634 handlers. The builder now writes the coordinator's C7 rows unchanged, except 0x7E9BFA44: it is the **t10 disconnect shell handler**, not "OlyApi FlashAir::disconnect", and 0x7EBF9F4C is a table word, not a vt word (check 4). Caller texts ("called by … sdk api handler n04 getPaperSetting") now use the right names |
| vt+48 vcall | every `mov (48,a2),a2; calls` was "schedule timeout" (A12, 0x7E9CDE02) | "schedule timeout" only when the vtable comes from `this` (tracked through register copies) and the class has statechart state words (OMReactive slot 12). 66 rows lost the label; 13 keep it |
| class prefix | range owner used before the function's own strings (C7-2 side finding 1: OlyHfwOpeBGrCtl) | order: own `X::` string / `.cpp` tag / `modules.tsv` → observer-member vtable → only callers are ctors of one class → interface vtable owner → neighbours (I) → 15c range. A prefix with no evidence of its own (strings, ctor, vtable with a known ctor, state code, getName, dispatcher, or callers/forwarder target with such evidence) is written **"X (range)"**, a location fact (5,612 rows) |
| "class not proven" | false when the class is provable through a singleton getter (A12) | lazy-singleton shape (`mov (RAM),aN; cmp 0; … new(N); ctor; mov a0,(RAM)`) is a `getInstance` row (+23 rows, e.g. 0x7E9678C8, F027 0x7E975E9D); a function that calls one getter and a virtual method on the result is "code in R range, wrapper of singleton C (getInstance G, RAM M)" (41 rows). Getter calls inside other rows print "getInstance G (RAM M)" instead of the getter's ctor actions. Family test fixed: "Ope facade" and "Ope API front" are no longer the same class (check 3) |
| missing main call | calls without a summary were dropped (A12, 0x7EAE6368 omitted 0x7EB55EAD(d0=2)) | every direct call is listed: "calls 0xX(d0=K)" plus the callee's own row (cut, with "...") or "(forwarder (args) -> T)" |
| constant arguments | `mov K,d0` on an error path, or a callee that overwrites d0 (checks 2, 3) | K must reach the call on every path (no branch target or ret/bra between) and the callee must read d0; a forwarder that moves d0 to d1 shows "(d0=K, passed on as d1)". A callee that switches on d0 gets no "[via …]" list when a constant is passed |
| `null-transition` | 9 of 10 sampled rows were exits (check 2) | popNullConfig + a cleared state word and no entry = **`exit-popnull`** "state exit: clears sub-state word +N; calls popNullConfig" (59 rows); no entry and no clear = `popnull-other` (17); `null-transition` only when a state is entered (6) |
| composite targets | transition steps named only the leaf; a conditional sub-state was shown as one branch (check 2) | state chains follow single state-word stores in any register: "4>49", "2>{9\|8}", "1>5". A composite entered through `this->vt+S` is not followed; the row says so ("[X calls this->vt+S first: an outer composite state set there is not shown]") |
| GEN target | 0x7EB871B1 always "GEN to self" (check 2) | the a0 object is tracked: "GEN to self" only when a0 = this, else "GEN to the object at +N" |
| `initStatechart` | zero-stores of non-state fields (check 2) | needs at least one known state word; else "zeroes fields …" (`member-init`) |
| `iface-thunk` | `mov (N,a0),a0; call T` outside any vtable called "interface thunk" (check 1) | outside a vtable it is a **member delegate** "calls T on the object pointer at this+N" (84 rows) |
| vtable owner | observer-member and member-object vtables named after the container class (checks 1, R1, R3) | owner = observer member when the storing ctor calls the observer base 0x7EB85D67 on `this`; a class ctor owns a vtable only when it stores it at this+0; else "(range)". Prologue rows now give the vtable address, not an owner |
| `initRelations` | relation setters that take a1 (check 5); silent cuts of member lists | a1 read before written excludes the rule; setTarget members are resolved through register copies; lists show "+N more" |
| `object-ctor` | dtor read as ctor; movhu zero stores missed; member-object vtables (checks 4, R3) | delete/vt+0 calls exclude; zero stores of any width; class "(range)" unless proven |
| `obs-ctor` | 15c "member of X (ctor caller C)" was wrong twice (R3) | cut to the fact "constructed by C"; empty update slots shown as "bare retf" |
| leaf summaries | "writes this+0" for copy loops; returns read from one path (checks 3, R2) | loop stores are "has a setlb loop (stores through aN)"; the return is stated only when every path into every ret loads a constant (d0, or a0 when d0 is never written) |
| new: `case-block` (I, 100 rows) | fwmap splits switch cases into functions (R2) | no direct caller, and a data word pointing here lies within 1 KB after a table that the preceding switch function (≤ 8 KB before) loads before `jmp (aN)`: "probably a switch-case block of S" |
| new: `static-init` (I, 17 rows) | static initialisers had no role (check 3) | entries of the function-pointer table 0x7ECB083C–0x7ECB0884 (19 words) |
| fwmap merges | F051 0x7EB94A3B holds slot 50 of vt 0x7EC8F440 (C7-3) | any vtable word that points inside a function adds "[fwmap merge: this function also holds N more entries: …]" (443 rows); leaf and dtor rules read only the code before the first merged entry |
| range splits | 15c ranges that hold another class | `OlyHfwOpePlyComSyncRsb` 0x7E981245–0x7E9815DA (strings "PlyComSyncRsb …", ctor 0x7E980EA7 calls 0x7E98130B; the 15c "OlyHfwOpeShoot getInstance 0x7E981245" is the PlyComSyncRsb getter) |

### 3.2 D7 changes (cycle 3: named errors fixed, context rows made specific)

**Fixes of named rule errors** (each one fixed by a rule, regenerated):

| Rule / part | Error (source) | D7 rule |
|---|---|---|
| vtable owner, ctor that calls a base ctor first | 0x7EB14946 named CmpPCom: vt 0x7EC6F70C is stored by the Cmp_PlayComponentBase ctor 0x7EB0A5E7 after its base ctor call, so the "stores at this+0" test lost `this` (C8-3 side finding 1) | `returns_this()`: a base ctor that ends `mov R,a0; ret` with R = the incoming a0 keeps `this` across the call (recursive). 443 vtables now have a ctor-proven owner (D6: 136) |
| vtable owner, "iface/member" | vt 0x7EBCDAC0 (pointer collection, 36 storers) named "EyeFi/FlashAir mode info" after one caller's ctor (A13-1, 0x7EA6C622) | "X iface/member" only when every storer is called by ctors of one class X; a storer that is not a 15c ctor but stores the vt at this+0 gives **"class of 0xS (stores this vt at +0; R range)"**; vtables stored from ctors of several classes are "shared class"; 0x7EBCDAC0 = **pointer collection** (table `VTNAME`). 15 "iface/member" vtables are left |
| "stores at this+0" | `inc4 a1` before a member vt store was not seen as a register change (round-1 check, 0x7E999670 stores vt 0x7EBCDB88 at +4) | any one-register instruction (`inc4`, `inc`, `asl2`, …) ends the `this` tracking of that register |
| class of a vtable slot | a slot function whose vtables have one proven owner took the range class (C8-3 F051: 0x7EB14946) | **`VTCLS`**: one owner that is not the range class → "C (vt owner; R range)" or "class of 0xS (…)"; several owners → no class from the range ("(range)") |
| class of a state handler | handlers in the life-test range named "life-test / self-adjust Ope" though their dispatcher is slot 33 of vt 0x7EC14F8C, Ope facade (self-test) (round-1 check, 0x7E9DAA3A) | **`HCLS`**: a handler takes the owner of the vtable whose slot-33 dispatcher reaches it, when proven and not the range class (269 rows "(vt owner; …)") |
| ambiguous short class names | `short()` cut "Ope facade (self-test)", "Ope facade (image count)", … to "Ope facade" | a 15c name whose short form is shared by several 15c classes is printed in full |
| member objects | 0x7EA3C09F "CapBlc setter (+4,this)": `this` is the member object at CapBlc+396 (vt 0x7EC3B8FC) (A13-2 #2) | **`member_of()`**: when every direct call site passes a0 = caller's this + K (K > 0, one K, one caller class; register tracking with copies, `add`, `inc4`), the class is written "X (range; every call passes a0 = this+K of C, N sites)" and callers no longer count as class evidence (645 rows) |
| own-string names | `[tag]func_name field` logs were not used as names (C8-2 F039 0x7EA29F77 `app_playinfo_control_move_target`) | **`own-name`**: (a) `[tag]name` with a snake-case name (≥ 2 underscores, not all capitals) and (b) `Class::method` in generic rows; the name must be the only one in the function's own strings and used by no other function. Row: "C = name() (own log name, "…"): …" (697 rows: 69 tag, 628 Class::method) |
| handler guards | branches that depend on 0x7EA7D270 / 0x7EA7D28D (CM "all started" / "all stopped") were shown as unconditional (C8-3 F051/F054) | a call whose d0 is compared next is a guard: "[result of 0xG tested]"; 0x7EA7D270 / 0x7EA7D28D are named functions (§2) (134 rows) |
| handler branches into shared code | the −2 timeout branch reached state 10 through the 12067 block; 16078 reached state 6 through a tail (round-1 checks) | from each jump that leaves the branch's own code (the next test's getCurrentEvent / null-check prelude, the ret tail and the parent fallback excluded), the straight run of instructions is added to the branch; entries found there are targets. A branch with no entry lists its direct calls "[calls 0xX]" (430 rows), and a jump not followed is shown "[continues in code shared with other branches at 0xT]" (201 rows) |
| dispatcher cases handled inline | a state handled in the dispatcher itself (vt+60 getCurrentEvent) was not counted: 0x7EB8891A "3 states (2,3,4)" (round-1 check) | every compare-chain value counts; a function with a single inline case is not a dispatcher |
| dtor with no vtable store | F042 0x7EA58A14 (CapPbr outer dtor) was a callee list (C8-3) | **`dtor-noreset`** (95 rows): slot 0, calls the OMReactive / Com_ base dtor, no vt store, `mov 0,a0; ret`: "C dtor (slot 0 of vt V; stores no vtable): calls T on +N (role); …; returns a0 = 0" |
| dtor bodies | only the first call was listed (round-1 checks: 3 WEAK) | all calls are listed ("…, then 0xA, 0xB") |
| big state entries with a payload switch | F050 0x7EAFB58D listed the first events only (C8-3) | **entry switch**: a compare chain on a field loaded from this+N right before the first compare: "switches on +F (N values, M targets; events built on each target's own path: …; code shared by several cases builds …)"; events per case from a control-flow reach, shared code reported separately. 8 rows; 4 entries lost the switch after the round-1 fix (field not loaded from `this`) |

**New rule for short functions: `body`** (1,296 rows, V). A function of ≤ 24 own instructions with only `mov`/`add`/`clr`/`ext`/`call`/`calls`/tail `jmp`, plus early exits (`cmp`/`btst` + `beq`/`bne` into the return tail), gets an exact ordered description: "straight-line body: if this+516 is non-zero (else returns); calls vt+44 of the object at this+516; sets this+516 = 0". Calls name the object (`on this+K`, `on the object at this+N`, `on the a0 result of T`; nothing when a0 = this or the callee does not read a0), constant d0/d1 only when the callee reads them, state entries called on `this` ("enters state 6 (0x7EB6C842)"), stores to this+N and RAM, and the return ("returns 1", "returns d0 of T", "returns a0 = 0"). A body called in a handler branch or by a state entry keeps that context. It replaced 1,296 generic rows (561 g:callers, 377 g:vtword, 167 g:vcall, 101 g:transition-action, …).

**Hand roles (10, V, each read in the code):** the four trimming-frame move steps 0x7EAE4BFF / 0x7EAE44E2 (F049) / 0x7EAE48FE / 0x7EAE496C (ops 1–4 of the state 75 entry 0x7EAE85DB), the Ctg 11799 action 0x7EB9E25C (F055), the CapPbr outer dtor 0x7EA58A14 (F042), the request-NAK override 0x7E97F5BD (vt slot 40, F034), the CapDpv timeout cancel 0x7EA0F865 + merged 0x7EA0F87D (F035), the CapMed busy predicate 0x7EA13AF5 (F036) and the media-access query 0x7E97A35E (A13-1). Texts in the TSV.

## 4. Coverage (same measure as D5)

`tiers.py`: **specific** = a table or shape rule gives the role; **partial** = generic but with own strings, api_* calls, events, vcalls, named callees, leaf summary or handler/entry context; **context** = only callers, a vtable slot or RAM addresses.

| Tier | D5 rows | D6 rows | D7 rows |
|---|---|---|---|
| specific | 23,751 (71.8 %) | 23,761 (71.8 %) | **26,261 (79.4 %)** |
| partial | 8,726 (26.4 %) | 8,311 (25.1 %) | **5,984 (18.1 %)** |
| context only | 612 (1.8 %) | 1,017 (3.1 %) | **844 (2.6 %)** |

D7: `body` rows count as specific (an exact description), `own-name` rows as specific (a name). The generic rows left (g:str 1,350, g:callers 1,465, g:vcall 733, g:leaf 406) are mostly functions with branches or loops, or larger than 24 instructions.

Context rows rose because uncertain content was cut: leaf returns that are not constant on every path, "[via …]" lists behind a d0 switch, and the "transition action" / "entry action" labels on pure helpers (no calls, no stores; 34 + 6 rows now plain leaf rows).

**Diff D6 TSV → D7 TSV:** 7,366 rows changed text, 2,109 changed rule code (606 g:str → own-name, 1,296 generic → body, 95 → dtor-noreset, 10 → hand), 1,331 changed I → V (body, dtor-noreset, hand rows), none V → I.

**Diff C7 TSV → D6 TSV:** 16,882 rows changed text (mostly the new "calls 0xX(d0=K)" items and the "(range)" marker), 393 changed rule code, 568 changed V/I (535 V→I: demoted rules and case blocks; 30 I→V: new getInstance rows).

## 5. Rule precision (D6)

**Method:** `samp.py` draws a seeded random sample of 10 rows per rule (rules with > 50 rows; later rounds exclude rows already checked). Each sample went to a checker agent with the rubric `CHECK-BRIEF.md`: read the code, judge every stated fact; **wrong** = any false fact (kind, class, state, event, slot, vtable, offset, argument, target, return); weak = true but thin (counted correct). Round 1 = seed 6060 on the first D6 build, round 2 = seed 7171 after the round-1 fixes, round 3 = seed 8282 after the round-2 fixes.

| Rule | Rows | R1 checked/wrong | R2 | R3 | Result |
|---|---|---|---|---|---|
| forwarder | 4,913 | 10/0 | | | V |
| getter-setter | 3,257 | 10/0 | | | V |
| handler | 2,673 | 10/0 | | | V |
| state-entry | 2,464 | 10/1 | 10/0 | | V (constant-argument fix) |
| g:callers | 2,038 | 10/0 | | | I |
| g:str | 1,999 | 10/2 | 10/2 | 10/1 | I; fixed 3 times (class, arguments, d0 switch); not re-sampled after the last fix |
| prologue | 1,656 | 10/1 | 10/1 | 10/2 | V after cut: all errors were vtable-owner names; rows now give the vtable address only (slot, vt and body were right in 30/30) |
| iface-thunk | 1,293 | 10/1 | 10/0 | | V (member-delegate fix) |
| ev-vtslot | 1,273 | 10/0 | | | V |
| ev-isTypeOf | 1,199 | 10/0 | | | V |
| composite-entry | 1,152 | 10/0 | | | V |
| ev-ctor | 1,015 | 10/0 | | | V |
| g:vcall | 901 | 10/0 | | | I |
| g:vtword | 736 | 10/0 | | | I |
| sdk-api | 632 | 10/0 | | | V |
| olyapi-method | 600 | 10/1 | 10/0 | | V (t10 shell handler fix) |
| gen | 461 | 10/1 | 10/0 | | V (class note, state-entry note) |
| g:transition-action | 420 | 10/1 | 10/0 | | I (pure helpers excluded) |
| g:leaf | 399 | 10/2 | 10/6 | 10/4 | I, cut: returns only when constant on every path; not re-sampled after the cut |
| g:api | 341 | 10/1 (+1 unsure) | 10/0 | | I |
| ctor | 317 | 10/0 | | | V |
| obs-ctor | 271 | 10/1 | 10/1 | 10/2 | V after cut: the errors were the 15c "member of" owner and an empty update; rows now say "constructed by C" |
| obs-update | 263 | 10/0 | | | V |
| object-ctor | 233 | 10/3 | 10/1 | 10/4 | **demoted**: I, "probably an object ctor", class "(range)" unless proven |
| g:entry-action | 221 | 10/2 | 10/0 | | I (pure helpers excluded) |
| cleanUpRelations | 200 | 10/0 | | | V |
| initStatechart | 168 | 10/2 | 10/1 | 10/0 | V |
| dtor-slot0 | 165 | 10/0 | | | V |
| dispatcher | 165 | 10/0 | | | V |
| getInstance | 162 | 10/0 | | | V |
| dtor-body | 156 | 10/0 | | | V |
| named | 153 | 10/0 | | | V |
| app_check | 116 | 10/0 (10 weak) | | | V (now with a summary) |
| transition-step | 113 | 10/2 | 10/2 | 10/1 | **demoted**: I, "probably a transition step" |
| g:state-exit | 105 | 10/0 | | | I |
| case-block (new) | 100 | | | 10/0 | I |
| facade-wrapper | 82 | 10/0 | | | V ("this+K" now filled) |
| initRelations | 81 | 10/5 | 10/1 | 10/1 | **demoted**: I, "probably initRelations (setter run)" |
| getName | 74 | 10/0 | | | V |
| dtor-base | 72 | 10/0 | | | V |
| g:callees | 65 | 10/1 | 10/3 | 10/0 | I |
| exit-popnull (new) | 59 | | 10/0 | | V |
| null-transition (D5: 82) | 6 | 10/9 | | | split into exit-popnull / popnull-other |
| **all** | | **410/39** | **170/18** | **100/15** | |

The round-1 zero-error rules were sampled on the first D6 build; later fixes changed their text only by shared parts (class marker, call lists, argument test), which the final check covers.

**Final check (seed 9393, 40 fresh rows of the final TSV, all rules, none sampled before):** 36 V rows, 4 I rows (rules: 11 forwarder, 6 getter-setter, 4 handler, 3 prologue, 2 each sdk-api / iface-thunk / ev-ctor / g:callers, 1 each state-entry, named, g:vcall, g:leaf, facade-wrapper, ev-vtslot, ev-isTypeOf, composite-entry). **0 wrong** (0 of 36 V, 0 of 4 I; 95 % upper bound about 8 % for V). After the sample, prologue rows lost their vtable-owner name (the 3 sampled owners were right).

**Named errors (all fixed by rules):** 0x7E9CDE02 = "code in OlyApi interface classes range, wrapper of singleton HLS root singleton (getInstance 0x7E9678C8, RAM 0x602B0C88): … vcalls +?->vt+48; called by 0x7E9BBE5B (sdk api handler q08 scWcsncat)" (no timeout); 0x7E9678C8 is a getInstance row; the BGrCtl functions with their own strings (0x7E98A854, 0x7E98ABD9, 0x7E98B0E4, 0x7E98B183 by its `.cpp` tag, 0x7E98B1CD, 0x7E98B2F7, 0x7E98B5A9) are "OlyHfwOpeBGrCtl (own string; OlyHfwOpeShoot range)"; the string-less ones between them say only what is proven (0x7E98B17A "OlyHfwOpeShoot (range) …", a vt-slot getter; 0x7E98B1B1 "class not proven (callers: OlyApi BackGroundCtrl::paint)"); 0x7EAE6368 lists "calls 0x7EB55EAD(d0=2)"; F051 0x7EB94A3B shows "[fwmap merge: … 0x7EB94A9E = vt slot 50 of 0x7EC8F440]".

### 5.1 Rule precision (D7)

**Method.** Round 1: `samp7.py` seed 7070 drew 10 rows per pool (all rows of a pool with fewer) from the first D7 build: every new rule, and for every changed rule only rows whose text changed against the D6 TSV. Four checker agents read them against the code with `CHECK-BRIEF.md` (D7 notation added). Round 2 (seed 8181, `samp8.py`, round-1 rows excluded): drawn after the round-1 fixes; the checker-agent limit was reached, so the coordinator read these rows in the code; three more defects found while reading them were fixed and the rows re-read (marked †). Wrong = any false fact; weak = true but incomplete (counted correct).

| Rule (pool) | Rows (final) | R1 checked/wrong | Error and fix | R2 checked/wrong | Result |
|---|---|---|---|---|---|
| body (straight-line) | 1,069 | 10/0 | — | 11/0; final check 1 wrong (return claim), fixed | **V** |
| body (with early exits) | 227 | 10/1 | class taken from the range for a handler's callee (0x7E9DAA3A); fixed by `HCLS` | 6/0 | **V** |
| own-name `[tag]name` | 69 | 10/0 | — | — | I (rest of the row is generic text) |
| own-name `Class::method` | 628 | (new after R1) | — | 10/0 | I (as above) |
| dtor-noreset | 95 | 10/0 | — | — | **V** |
| hand | 10 | 10/4 | "h/w = s16": the height/width fields are read u16 (`movhu`, no `exth`) in all four trimming steps; fixed | 10/0 | **V** |
| handler (changed rows) | 783 | 10/4 (+2 weak) | branches that reach the entry through shared code showed no target; fixed (shared-code runs). † the next test's prelude, a vt+60 prelude and the parent fallback were reported as "shared code"; fixed | 10/0 † | **V** |
| state entry with switch | 8 | 8/2 | switch field not loaded from `this` (0x7EAFAAF4); cases sharing one target and the fall-through default (0x7EAF9177); fixed (4 rows lost the switch) | 4/0 (all rows left) | **V** |
| dtor-slot0 (changed) | 140 | 10/1 | "class of 0x7E999670": `inc4 a1` not tracked, vt stored at +4; fixed | 10/0 | **V** |
| dispatcher (changed) | 164 | 10/1 | inline-handled state not counted (0x7EB8891A); fixed. † a single inline case made a handler a "dispatcher" (0x7E9E6065); fixed | 11/0 † | **V** |
| getter-setter (changed) | 562 | 10/0 | — | — | V |
| iface-thunk (changed) | 980 | 10/0 | — | — | V |
| vt-owner class prefix ("class of", "(vt owner;") | 384 | 10/0 (1 weak) | — | 7/0 | V |
| member-object prefix | 645 | 10/0 | — | — | V (location/call-site fact) |
| getName (changed) | 74 | 10/0 | — | — | V |
| dtor-body (changed) | 149 | 10/0 (2 weak: later calls left out; fixed) | — | 7/0 | V |
| **all** | | **148/13** | | **86/0** | |

Rules not changed in D7 keep their D6 measurement (§5 table); their text changed only through the shared class prefix (vt owner, member, "(range)"), which the pools above and the final check cover.

**Final check (seed 9494, `fin40.txt`, 40 fresh rows of the final TSV, all rules, none sampled before):** 34 V rows, 6 I rows (rules: 7 handler, 5 forwarder, 4 each prologue / iface-thunk / getter-setter, 3 state-entry, 2 each body / ev-isTypeOf / g:str, 1 each getInstance, facade-wrapper, ctor, g:transition-action, g:leaf, g:vcall). **1 wrong of 34 V rows (2.9 %; 95 % upper bound about 15 %), 0 wrong of 6 I rows; 3 I rows weak.** The wrong row was `body` 0x7E99162D "returns d0 of 0x7E991766": that callee is `add 124,a0; retf`, sets no d0, and the function returns the pointer in a0. **Fixed after the check (rule):** "returns d0 of T" is now written only when T calls nothing and writes d0 itself; otherwise no return is stated (204 `body` rows lost the return clause, 4 keep it, each read). The other 39 rows did not change. The 3 weak I rows: an unresolved "+?" (+1304) and missing u16 stores (0x7EA34159), an own-string role not used ("createActiveRelations", 0x7EAD4233), a setlb loop not described (0x7EB8641A).

## 6. Reading a row (examples, V unless marked)

- `0x7EAD203B CmpERaw_EditRawComponent choice (null transition, popNullConfig) on +572: 28 cases 1->38>39, … 403->65>66, …; default -> 48` (review 3 F041).
- `0x7EB1AB41 CmpPCw_PlayCwComponent state 10 (also parent of states 7,8,9) handler: 11563 … -> state 3 [notify (via 0x7EA7DB63)]; 11562 … -> state 4>49; no parent fallback (returns 0)` (D6: composite 4 now shown).
- `0x7EAABB5E CmpPCom_PlayCommonComponent state exit: clears sub-state word +872; calls popNullConfig (sub-state exits via 0x7EAAC599, …)` (D5 called it a null transition).
- `0x7EA81DF1 Cmp_StillShootingComponentBase probably a transition step: exit (0x7EA81DE9) then enter states 2>{9|8} (via 0x7EA81F9D); returns 1` (I; the sub-state depends on (+472)->vt+12).
- `0x7EAE6368 CmpETri_EditTrimmingComponent state 57 entry (+1124/+212): calls 0x7EB0EC7E (forwarder (d0=0, d1=5636) -> 0x7E5082B6); calls 0x7EB55EAD(d0=2); builds 12067 …; GEN to self; "…::single_mode_start#"` (A12).
- `0x7E975E9D Ope facade (range) getInstance (lazy singleton at RAM 0x602B1FEC: new(396) + ctor 0x7E975D65, stored there)` (C7-2 F027).
- `0x7EA1A2EB CapThr_ThroughImage (range) probably a switch-case block of 0x7EA1A1B9, not a function (… table word 0x7EC2FDA8 near table 0x7EC2FD6C …)` (I).

- D7: `0x7EB6C7BA CmpPSou_PlaySoundComponent straight-line body: calls 0x7EB6C7D1 (… sets field +208 = 1 …); calls 0x7EA7CE74; enters state 6 (0x7EB6C842)` (A13-2 #3).
- D7: `0x7EB14C54 Cmp_PlayComponentBase state 7 handler [timeout handler]: -2 OXF timeout event -> state 10 [result of 0x7EA7D270 (CM all-started check) tested]; 12067 … -> state 10 [same guard]; 3346 … -> state 7; else parent 0x7EB14BA3` (C8-3 F051).
- D7: `0x7EAFB58D Cmp_PictBridgeComponent state 135 entry (+1352/+1296): switches on +576 (8 values, 9 targets; …: 0 -> builds 13787; 1 -> builds 13795; 2 -> builds 13899, 13785; 3 -> builds 13899, 13784; 4 -> 13899; 5 -> 13899; 6 -> 13809; 7 -> 13810; other -> no event; code shared by several cases builds 7091, 12067)` (C8-3 F050).
- D7: `0x7EA29F77 CapPls_PlayState (range) = app_playinfo_control_move_target() (own log name, "[chls]app_playinfo_control_move_target target_no"): …` (I; C8-2 F039).
- D7: `0x7EA3C09F CapBlc_BlurringCorrection (range; every call passes a0 = this+396 of CapBlc_BlurringCorrection, 1 site) setter (+4,this) = arg` (A13-2 #2).

## 7. Corrections to older sections and reviews

1. **Review round 6 batch 3, F033 and "weakest areas" item (CapThr entry-state ids):** the constants have one more non-zero byte than the review lists. F033 0x7EA1C7C5 writes **0x02010201** (`mov 33620481,d0` at 0x7EA1C7CB), not 0x02010001. The 14 setters 0x7EA1C740…0x7EA1C9D7 set, in address order: 0x02030202, 0x02030201, 0x02010202, 0x02010201, 0x02010102, 0x02010101, 0x01030202, 0x01030201, 0x01030102, 0x01020202, 0x01010202, 0x01010201, 0x01010102, 0x01010101 (V, `mov K,d0` before `call 0x7EA1A8A2`). After the write, the 0x02xxxx01 setters (0x7EA1C76E, 0x7EA1C7C5, 0x7EA1C81C) follow the F033 pattern (Restart_Through(this, 0) through 0x7EA1D604 when this+264 = 1); the 0x02xxxx02 setters call 0x7EA1DF9E and the 0x01xxxx01 setters call 0x7EA1E03E (both reach `[CapThr]exec buffering instruction` 0x7EA1E2BF); the 0x01xxxx02 setters call 0x7EA2010E (event 26853, `execReserveSeqCmd`) (V calls; the meaning of the bytes is I). Other writers of the entry state: 0x7E96F410, 0x7E988079, 0x7E99775A, 0x7EA388B8.
2. **Review 3 F046:** 0x7EB1AB41 is also the **state-10 handler** of CmpPCw, not only the parent of 7/8/9: jump table 0x7EC70994, index 7 → 0x7EB1A9C8 `call 0x7EB1AD88` → forwarder → 0x7EB1AB41 (V).
3. **Review 3 F041 / 15c §4.2:** the review's RAW-only targets 403→65, 404→57, 406→50, 407→62, 408→54 are composite states; their default sub-states are 66, 58, 51, 63, 55. 15c §4.2 lists the leaf state (e.g. 1 → 39); the composite is 38 (V). Every play class's choice is now a row (34 `choice` rows), so the per-class extensions of the §4.2 table can be read from the index.
4. **15c row "Cab_CameraBase facade"** holds three classes; see §1 (Bufferd 0x7EB8AD37–0x7EB8BCCA, I by ctor order). The 15c Bufferd text (state-7/8 entries 0x7EB8B66F/0x7EB8B8EA, exit 0x7EB8B86A) fits that sub-range. Its state-7 entry uses `mov 7,a1; mov a1,(316,a2); mov a1,(172,a2)` (V), which the 13c §3 `mov K,d0` entry signature does not match.
5. **16a D4 rows** for 0x7E966C01 / 0x7E966CCE ("HIGHLEVEL_MAIN / HLS startup method") were range artefacts: they are the generic pointer collection add/remove (§2), used across the app layer (V). **fwmap:** 0x7E966CCE (88 B) includes a second function, the get(i) accessor 0x7E966CFF, after its `retf` (V).
6. **13c §3 shape catalogue:** add the D5 shapes of §3 (choice compare chain; split / register / pushNullConfig-first entries; RAM-global getters; history writes).
7. **06 §5 / C7-2 item 2 (D6, V):** 0x7E9BFA44 is the `sdk api` handler **t10 disconnect** (string `OlyShell_FlashAir__disconnect`): it calls getInstance 0x7E9C458C and vt+36 = the real wrapper 0x7E9C4648, then prints the API name 0x05060A. The C7 row "OlyApi FlashAir::disconnect … vt word 0x7EBF9F4C" was wrong twice: 0x7EBF9F4C is the handler field of the last table entry.
8. **15c row "OlyHfwOpeShoot (+PlyMov, BGrCtl)" (D6):** its start 0x7E981245 and "getInstance 0x7E981245" belong to **OlyHfwOpePlyComSyncRsb** ("PlyComSyncRsb new pResParam", RAM 0x602B2028); the PlyComSyncRsb code runs to 0x7E9815DA (I: strings at 0x7E981245, 0x7E98128B, 0x7E9813A4; initStatechart 0x7E98130B called by ctor 0x7E980EA7; dispatcher 0x7E981322 = slot 33 of vt 0x7EBE7690). BGrCtl is 0x7E98A854–0x7E98B5A9 (own strings, V); PlyMov strings run 0x7E981663–0x7E981F92.
9. **15c member-of claims (D6 checks, V):** observer 0x7EB8E170 is built by 0x7EB8D8FE (Dev display/play handle holders, vt 0x7EC8E030), not by the Cab_CameraBase facade; observer 0x7EB3D9EA is built by the static initialiser 0x7EB08CA4 as a global at RAM 0x605EA81C, not by Cmp_PlayComArchitecture. 0x7E9EF709 is the **Cap init base ctor** (vt 0x7EC20390, base Com_ init-chart 0x7EB87AC9), the base of 34 Cap_ classes, not a CapDpc_DisplayControl function.
10. **15c ranges that hold a second class (D6 checks, V):** "life-test / self-adjust Ope" 0x7E9D773A–0x7E9DB226 also holds the life-test statechart of ctor 0x7E9D79EA (vt 0x7EC14F8C, member at +324 of 0x7E9D7473); "OlyHfwOpeSndCtl" holds a facade-registry singleton (getInstance 0x7E9E59A9, RAM 0x602B2718, ctor 0x7E9E5809, vt 0x7EC1B244) and a 20-B object (ctor 0x7E9E51F8, vt 0x7EC1AA7C); "Com_ component-manager base" 0x7EB87E25–0x7EB89133 holds the level-2 Com_ reactive ctor 0x7EB88CED and its initStatechart 0x7EB88E14. Member-object vtables of CapRec_Record (+112, vt 0x7EC3FA14, `CapRec_NotifyProgressObserver`), CapOef_EffectManager (+112, vt 0x7EC42668) and OlyHfwOpe CustomPrint (+124 of @7E991647, vt 0x7EBEE2C4, ctor 0x7E98D2E3) sit in the container's range.
11. **fwmap (D6):** 443 functions hold more than one vtable entry point (e.g. F051 0x7EB94A3B also holds 0x7EB94A9E, slot 50 of vt 0x7EC8F440; 0x7EA8B752 holds slots 144–146 of vt 0x7EC4FB94); about 100 "functions" are switch-case blocks (case-block rows), e.g. 0x7EB0FA59 (1,522 B) in the switch 0x7EB0F99A on +572, whose fwmap size (80 B) is cut.

12. **D7 (C8-3 side finding 1, V):** 0x7EB14946 is slot 33 of vt 0x7EC6F70C, which the Cmp_PlayComponentBase ctor 0x7EB0A5E7 stores at this+0 after its base ctor 0x7EA7C89C (which returns this); the row is now "Cmp_PlayComponentBase rootState_dispatchEvent". The same fix gives 443 vtables a ctor-proven owner.
13. **D7 (A13-1, V):** 0x7E966BD1/0x7E966BD6 and every "[target role: …]" that copied them now say "pointer collection dtor (slot 0 of vt 0x7EBCDAC0)", not "EyeFi/FlashAir mode info iface/member dtor".
14. **D7 (A13-2 #2, V):** the CapBlc setters 0x7EA3C09F / 0x7EA3C0A5 / 0x7EA3C0AB act on the member object at CapBlc+396 (vt 0x7EC3B8FC, ctor 0x7EA3BFAC); the CapBlc field written is +400 (+404, +408).
15. **D7 (round-1 checks, V):** handler rows in the life-test range 0x7E9D773A–0x7E9DB226 whose dispatcher is 0x7E9D84EF (slot 33 of vt 0x7EC14F8C, ctor 0x7E9D79EA) belong to **Ope facade (self-test)**; only the 2-state chart of vt 0x7EC146BC (dispatcher 0x7E9D77C4) is the life-test class. 0x7E999670 stores vt 0x7EBF0CE0 at +0 and the member vt 0x7EBCDB88 at +4.
16. **D7 (C8-3 F049/F055, C8-2 F034–F036):** the hand roles of §3.2 replace the context-only rows; the review texts are right except two details: in 0x7EB9E188 the copy +384 → +388 is unconditional (the 11–18 test only repeats the store), and the trimming height/width fields +1084/+1082 are u16.

## 8. Open questions

1. Cap interface bodies (CapImg, CapPls, CapMed, CapPbr) and Dev part 2: rows are mostly partial (what they call and write), not specific. A slot dictionary per interface (who calls `+K->vt+S` and with which strings) would name them; the resolved `vcalls` offsets (+828 CapDpv, +832/+860 play devices, +200 sequence parts) are the input for it.
2. "code in X range, class not proven" (2,503 rows) and "X (range)" (5,612 rows): many are base-class methods used only by derived classes, or class-family helpers. A sub-range split by string clusters (as for the SndCtl tail, touch-panel Ope code from about 0x7E9E4B3D) would give them a class.
3. The meaning of the CapThr entry-state bytes (0xAABBCCDD: AA ∈ {01, 02}, BB ∈ {01, 02, 03}, CC/DD ∈ {01, 02}) (I: mode / view / sub-mode).
4. OMReactive slots 3, 10, 26, 31, 34 are still unnamed; the class names of the print facade 0x7E991647 and the 30+ "Ope/app class @…" rows of 15c.

## Known rule errors and limits (after D7)

Fixed in D7 (rules, regenerated): vtable owner lost across a base-ctor call; "iface/member" owners from one caller's ctor (pointer collection named EyeFi/FlashAir); `inc4` in the this+0 test; range class for vtable-slot functions and for state handlers (vt owner); ambiguous short class names; member objects named as the container class; `[tag]func_name` and `Class::method` own names unused; dropped handler guards; branches that reach their entry through shared code; inline dispatcher states; dtors without a vt store; dtor bodies listing one call; entry switches on a payload field; the four trimming steps, F055, F042, F034, F035, F036 as callee lists. Still open:
- **Class from the 15c range** where no vtable, handler or call-site fact applies: rows say "X (range)" (6,286 rows) or "code in R range, class not proven". Functions reached only through `this->vt+S` of a derived class keep the range class.
- **Demoted rules (I), unchanged from D6:** `object-ctor`, `transition-step`, `initRelations`; `g:str` and `g:leaf` not re-sampled after their last D6 fix. `own-name` rows stay I: the name passed 20/0 checks, the rest of the row is generic text.
- **Handler branches:** a branch that acts only through `(N,a2)->vt+K`, or whose shared code is more than one jump away, shows its direct calls or "[continues in code shared with other branches at 0xT]", not its target. Branch side effects other than events, notifies and guards (field stores, counters) are not listed.
- **`body` return clause (final check):** a function that ends right after a call states its return only when the callee calls nothing and sets d0; callees that return a pointer in a0 are not described.
- **`body` rule limits:** arguments in a1 and registers copied from call results are not listed; "(else returns)" gives no value when the return register is set before the guard (e.g. 0x7EA91ED3 returns 1 on the early exit); 35 rows keep "+?" for a virtual call whose object the tracker did not resolve.
- **Entry switches:** only compare chains on a field loaded from `this` right before the first compare (8 entries); jump-table switches and switches on a member object's field (0x7EAFAAF4: [+696]+0) are not shown.
- **"+?" vcall objects** from stored arguments or caller registers (case blocks) are not resolved in generic rows.
- **Leaf summaries** do not describe out-parameter writes or loop sizes; the return of a function that leaves d0 unchanged is not stated.
