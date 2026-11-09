# Audit A14: random index rows, batch 1 (5 per index)

## 16a-app-function-index 0x7EBA139E

0x7EBA139E	32	Dev boot device (range) straight-line body: calls 0x7E68CD13 (d0=0xFFFFFF); calls 0x7EB86ED0 observer list notify-all (vt[2] filter, vt[0] update) on the object at this+8	body	V

## 16a-app-function-index 0x7EA35E95

0x7EA35E95	7	CapTak_Take (range; every call passes a0 = this+332 of CapTak_Take, 1 site) setter (+968,this) = arg	getter-setter	V

## 16a-app-function-index 0x7EA3D170

0x7EA3D170	11	CapCDH_ContinuousDisplayHandle (range) method: leaf: writes this+4; called by 0x7EA3D11A (class of 0x7EA3D109 (stores this vt at +0; CapCDH_ContinuousDisplayHan...)	g:leaf+callers	I

## 16a-app-function-index 0x7E9D865D

0x7E9D865D	3	life-test / self-adjust Ope (range) probably a switch-case block of 0x7E9D84EF, not a function (no direct caller; table word 0x7EC14DCC near table 0x7EC14DC8 loaded by 0x7E9D84EF, which jumps through a register)	case-block	I

## 16a-app-function-index 0x7EB1D279

0x7EB1D279	14	CmpPCw_PlayCwComponent state 42 entry (composite: sub-state word +872 = 42) then enters state 43 (0x7EB1D2D6)	composite-entry	V

## 16b-gui-function-index 0x7ED8C7E4

0x7ED8C7E4	56	OlyApi wrapper: SettingController::getSetting; pointer-to-member target stored into the object by ctor 0x7ED8C1DA; does: getSetting(281)	api,pmf,args	V

## 16b-gui-function-index 0x7EDF2A18

0x7EDF2A18	13	page class (pages 626) vt slot 0 (+0) = destructor; short wrapper → 0x7EDEE182	vt,shape	V

## 16b-gui-function-index 0x7ED3A5F5

0x7ED3A5F5	103	panel 107 (type 0x604F) vt slot 100 (+400) = OnDBUpdate (GM 0x1901/0x1902); does: DM get block 0, DM get block 62	vt,args	V

## 16b-gui-function-index 0x7ECEE628

0x7ECEE628	5	pointer entry of 0x7ECEE62D (`movm`/`add -N,sp` frame set-up for calls through a pointer; falls through into the body, where direct calls enter); root object 0x0001 vt slot 12 (+48) = getRect (by value), shared by 151 more vtable(s)	pentry,vt	V

## 16b-gui-function-index 0x7EDF9FD0

0x7EDF9FD0	121	page class (pages 649) vt slot 2 (+8) = enter/redraw(mode); does: pageBaseEnter, DM get block 27, DM set block 27, setGuide(0 "", 0), ShowPanelEx(4), guiFlag6277, setPalette	vt,args	V

## 16c-platform-function-index 0x7E5798CA

0x7E5798CA	141	buff buffer-pool manager	uses strings “ucRemain” | “(ALLOC) (ADDRESS)   (ID)” | “---------------------------------”; helper of 0x7E5789FB (only caller), under 0x7E5776A2 (`buff` shell (print/alloc/free))	own strings + call graph	V

## 16c-platform-function-index 0x7E457B07

0x7E457B07	42	prm settings store	`prm size` EEROM: rebuilds EEROM defaults into 0x603F4674 (0x7E4579EA, side effect) and returns end 0x604DE510 - base; straight-line: calls 0x7E45601F (bank field getter) with a0 = u32[0x60414684 (prm bank descriptor ptr EEROM)]; calls 0x7E4579EA (pack ROM default data (a1 list, headers skipped) into…) with d0 = 0x10000, a0 = 0x603F4674, a1 = ret(0x7E45601F); returns d0 = u32[0x604DE510 (end ptr of EEROM RAM image)]+0x9FC0B98C; helper of 0x7E456928 (`prm` shell (getval/setval/clear/dump/psave/pload/fmem …)) (only caller)	D5 read (prm): caller shell `size` + straight-line summary (calls, no branch) + call graph	V

## 16c-platform-function-index 0x7E45E491

0x7E45E491	79	GIO helpers / CCD temperature task	branch summary: calls 0x7E436577 (sns_ctx); if (u8)ret(0x7E436577) == 1: [calls 0x7E449083 (OlyEvSt) with d0 = (s16)u16[0x7E43EB5E], d1 = 1; if ret(0x7E449083) == 0: [returns] else: [calls 0x7E426D4B (error recorder) with d0 = 0x19002B10]] else: [calls 0x7E449030 (OlyEvSt(Cpu)) with d0 = (s16)u16[0x7E43EB5E], d1 = 1; if ret(0x7E449030) == 0: [returns] else: [calls 0x7E426D4B (error recorder) with d0 = 0x19002B10]]; logs error 0x19002B10 (per drivers) via the recorder 0x7E426D4B; address taken (no direct caller): address loaded at 0x7E45E3B9 in 0x7E45E38D, stored at +32 of a0; address loaded at 0x7E45E3FB in 0x7E45E3CF, stored at +32 of a0; add

## 16c-platform-function-index 0x7E545590

0x7E545590	117	IMG image-job library > IMG job API, ISRs, job builders	runs a caller-given IMG job: job preparation 0x7E54D5E4, 0x7E54D64C, IMG_END wait 0x7E55EB40 loop, 0x7E54D6E9 (no 320-B descriptor of its own; callers img_exec 0x7E544BB5 and 0x7E545605)	D5 read (d6fix): D6 check id 138 (13a text copied to 3 rows)	V

## 16c-platform-function-index 0x7E45A76E

0x7E45A76E	79	accelerometer per_acc/acc_spi	acc bus open (blocking), d0 = 7-bit device address: takes 'ACC_SPI' sem, sio_request(3, grant cb 0x7E45AA2C) retried every 16 ms, waits grant flag 0x7E45AAA7, stores addr<<1 at 0x604149E0; service calls: OlySmWt; sio_request(3); OlyTaSS sleep(16); OlySmSi; calls kernel services OlySmWt, OlyTaSS (sleep), OlySmSi(Cpu)	D5 read (drv): OlySmWt id 0x7E43EB22; 0x7E469961(3); add d2,d2; called with 24 (0x18) + callee signatures + kernel wrappers (callees)	V

## 16d-core-play-overlay-index 0x7F0879FA

0x7F0879FA	86	under DPS pool malloc (<1024 B: 5 size classes … 0x7F0879CD (direct caller)	features+call graph	V	C	overlay B: DPS_MAIN PictBridge app (DPS pool malloc 0x7F0879CD, file transport) (I, position)

## 16d-core-play-overlay-index 0x7E939980

0x7E939980	397	calls `memcpy (fast)` 0x7E5081FA; under ACP server PUT op (0x02/0x82) 0x7E9397FD (direct caller)	features+call graph	V	C	OBEX_ACP and OBEX tasks

## 16d-core-play-overlay-index 0x7E6A8824

0x7E6A8824	9	probably: returns u32 0x605AB388 (stabiliser time stamp)	D5 exp decode (exp/hand_exp.tsv): code	I	S	EXP_MOVIE `exp` module (live-view/movie AE)

## 16d-core-play-overlay-index 0x7F09E31F

0x7F09E31F	1443	probably as a section says (not checked here): “called by the scene code 0x7F09E31F”	sec 08 line 223	I	S	overlay B: C3D scene code (photo-room slideshow; scene start 0x7F09E9EE, init 0x7F0A13F9, teardown 0x7F09EAAC; 14a §3, 08)

## 16d-core-play-overlay-index 0x7E6E0671

0x7E6E0671	486	`AvmidApi_param_init` (logs its own name)	own string (bare)	V	S	movie mov*.c (MOV_* tasks, recorders, AVI/MOV writers, movie playback)

## 16e-graphics-avpi-index 0x7EE7EAF7

0x7EE7EAF7	264	C3D framework > class code	shared helper, 2 callers: 0x7EE855B6 (vtable slot +56 of C3D class id 21); calls 0x7EE74A75 (null-checked getter: returns or 0), 0x7EE75DFB (C3D object class-id getter), 0x7EE74ABD (C3D virtual-call stub: returns 0 when a0 or its class block is NULL, e)	call graph	V	P

## 16e-graphics-avpi-index 0x7EE792B1

0x7EE792B1	16	C3D framework > class code	setter: +168 = d0 (NULL-checked); helper of 0x7EE7C64F (C3D unpack a property record into about 30 checked setters 0x7EE79235.)	shape + call graph	V	S

## 16e-graphics-avpi-index 0x7EEB97A1

0x7EEB97A1	5	AVPI > plug-ins	vtable slot 6 (+24) of AVPI class vt 0x7F03147C (created only from Video Decode Plug-in code: ctor callers); pointer entry (prologue `movm`) of 0x7EEB97A6	AVPI vtable 0x7F03147C word 0x7F031494 + two-entry rule (≤ 6 B movm/add, next start)	V	S

## 16e-graphics-avpi-index 0x7EE15353

0x7EE15353	539	DMP GL > GL back end (state blocks, uniforms; I)	uses memset; helper of 0x7EE15060 (I: build the `gl_*` uniform table)	runtime callees (13a, 14a) + call graph	V	P

## 16e-graphics-avpi-index 0x7EE9053A

0x7EE9053A	5	AVPI > framework classes	vtable slot 5 (+20) of AVPI class vt 0x7F02F6A0; shared by 5 vtables; pointer entry (prologue `movm`) of 0x7EE9053F	AVPI vtable 0x7F02F6A0 word 0x7F02F6B4 + two-entry rule (≤ 6 B movm/add, next start)	V	S

