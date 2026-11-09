# Audit A13: random index rows, batch 1 (5 per index)

## 16a-app-function-index 0x7EA6C622

0x7EA6C622	3	virtual entry (prologue only) of the next body 0x7EA6C625 [vt slot 0 of vt 0x7EC4810C] = code in Cap_PlaySlide (slideshow) + CmpShc_ShootingSequenceBase range, class not proven (callers only in OXF runtime / CmpSts_RecordController): forwarder (this+12) -> 0x7E966BD6 [target role: EyeFi/FlashAir mode info iface/member dtor (slot 0 of vt 	prologue+body	V

## 16a-app-function-index 0x7EB2796E

0x7EB2796E	63	CmpPEvc_PlayEvcollectionComponent parent of state 37 handler: 12067 evTraCmp_NextState -> state 49; else parent 0x7EB2511F	handler	V

## 16a-app-function-index 0x7E97A359

0x7E97A359	5	virtual entry (prologue only) of the next body 0x7E97A35E [vt slot 1 of vt 0x7EBE3940] = code in Ope/app class (base Ope request base (level 3)) @7E979D72 range, class not proven (callers only in Ope facade / Ope media-access counter): [via 0x7E974A85: "get UNKNOWN MEDIA ACCESS STATE!"]; called by 0x7E9798AA (code in Ope facade range, cl	prologue+body	V

## 16a-app-function-index 0x7E9A03F3

0x7E9A03F3	28	sdk debug shell (range) method: calls 0x7E9A053F (forwarder -> 0x7E975CD3); [via 0x7E9E5737: (via 0x7E9E5A46: pointer-collection remove())]; vt slot 5 of sdk debug shell (range)	g:vtword	I

## 16a-app-function-index 0x7EB2A250

0x7EB2A250	8	CmpPEvV_PlayEventViewComponent forwarder -> 0x7EB2A258 [target role: CmpPEvV_PlayEventViewComponent state 17 entry (+884/+212): calls 0x7EB0EC7E (forwarder (d0=0, d1=5636) -> 0x7E5082B6); c]	forwarder+tgt	V

## 16b-gui-function-index 0x7ED24D23

0x7ED24D23	173	panel base vt slot 63 (+252) = selectLayout(0..3), shared by 115 more vtable(s); returns e.g. 1	vt	V

## 16b-gui-function-index 0x7EDEB068

0x7EDEB068	36	page class (pages 329) vt slot 3 (+12) = key(d0 = page key, d1)	vt	V

## 16b-gui-function-index 0x7ED71155

0x7ED71155	58	private method (in panel 29 (type 0x601C) code); called by 0x7ED70C5E (calls widget setters [position, visibility, list index])	range	I

## 16b-gui-function-index 0x7ED497B1

0x7ED497B1	232	panel 108 (type 0x6050) vt slot 100 (+400) = OnDBUpdate (GM 0x1901/0x1902); does: DM get block 0, DM get block 4, DM get block 5, DM get block 77, DM get block 6	vt,args	V

## 16b-gui-function-index 0x7ED810C3

0x7ED810C3	119	calls widget setters (visibility); private method (in panel 9 (type 0x6009) code); called by 0x7ED805E9, 0x7ED808DD +1; does: setVisible	synth,range,args	I

## 16c-platform-function-index 0x7E5CA752

0x7E5CA752	99	file wrapper / VFS	rename(a0 old path, a1 new path): splits the new name, path walk on the old path with op mask 1 -> 0x7E5B604F writes the new 8.3 name; 0 / -1	D5 read (dpof): read: 88ef, temp FILE on stack, mask 1	V

## 16c-platform-function-index 0x7E550927

0x7E550927	6	IMG image-job library > IMG constant/table getters	constant getter: returns 211; leaf: returns d0 = 211; helper of 0x7E57A140 (only caller), under 0x7E55FFA3 (IMG_PRECON cmd 3 (WB))	shape: mov imm; retf + leaf summary (straight-line, no call) + call graph	V

## 16c-platform-function-index 0x7E5853A1

0x7E5853A1	341	take shell / TAKE_EXPOSE (TakeExp)	logs error 0x25000702 (TAKE) via the recorder 0x7E426D4B; service calls: prm getval(0x8551, 0x8D21); EXP command(0x701, 0x501, 0x700, 0x505); helper of 0x7E5829E8 (TAKE_EXPOSE task: TakeExp hash table 0x7E791478 (key = cmd+1) (only caller)	error codes (0xMM00SSNN) + callee signatures + call graph	V

## 16c-platform-function-index 0x7E50F101

0x7E50F101	29	UI LED / UI_OUT / UI_SCREEN / jog dial	leaf: in a loop x18 (first-pass values): u8[0x604F3F7C] = 1; u8[0x604F3F7D] = 1; helper of 0x7E50D7CD (only caller), under 0x7E503DD4 (Usr0 startup task: starts ~60 tasks in a fixed order (OlyTaS)	leaf summary (straight-line, no call) + call graph	V

## 16c-platform-function-index 0x7E5A5EF5

0x7E5A5EF5	334	TAKE sequencer states and handlers	helper of 0x7E5A605B (only caller), under 0x7E5A2A6F (TAKE_MAIN handler for StlLiveTake B-event 0x1B)	call graph	V

## 16d-core-play-overlay-index 0x7E91D925

0x7E91D925	17	probably: returns 1 if the link's tx packet list (+232) is non-empty	D5 BT decode (bt/hand_bt.tsv): code	I (D6: demoted; V)	S	L2CAP

## 16d-core-play-overlay-index 0x7E68029F

0x7E68029F	42	under case 0x60000 of 0x7E67F3E6 0x7E67F49F (direct caller)	features+call graph	V	C	C camera API api_*.c (api_exec_start queue table)

## 16d-core-play-overlay-index 0x7E7071EF

0x7E7071EF	50	probably: index of GUI value d0 in the gui[] array of record a0; 0 when not found or no gui[]	D5 mcon/Apical decode (mcon/hand_mcon.tsv): code	I (D6: demoted; V)	S	value-list engine and the two ROM→RAM hash tables

## 16d-core-play-overlay-index 0x7E67DD54

0x7E67DD54	118	under `setExclusion` 0x7E9D6160 (direct caller), `api_event_Check_EntryCustomEvent` 0x7E67DDCA (2 levels up)	features+call graph	V	C	C camera API api_*.c (api_exec_start queue table)

## 16d-core-play-overlay-index 0x7F0933B0

0x7F0933B0	25	under `tpc_control` 0x7F089208 (2 levels up)	features+call graph	V	C	overlay B: PTPCOM transaction engine, ptp_register 0x7F08E975, PTP/MTP op handlers (I, position)

## 16e-graphics-avpi-index 0x7EE36B89

0x7EE36B89	301	3D engine core > MB/MT format loaders	MT animation-loader sub-parser: up to 3 key arrays (u16 count, alloc, fill, ascending-time check); helper of 0x7EE35EE6 (format loader for MT files)	curated: review r5 F074 + call graph	V	S

## 16e-graphics-avpi-index 0x7EE83BAC

0x7EE83BAC	18	C3D framework > class code > in the code block of class id 51 (by position, I)	wrapper of 0x7EE83AF0 (calls vtable slots of the argument a1: +0 ×1, +12 ×1; 2 of its 2 indir); helper of 0x7EE83901 (vtable slot +8 = read of C3D class id 51; override chain: root/ancesto); calls 0x7EE83AF0 (calls vtable slots of the argument a1: +0 ×1, +12 ×1; 2 of its 2 indir)	shape + callee role + call graph	V	S

## 16e-graphics-avpi-index 0x7EEC3A8B

0x7EEC3A8B	484	AVPI > SCA session control	vtable slot 29 (+116) of AVPI class vt 0x7F031B54; helper of 0x7EEC3D55 (vtable slot 32 of AVPI class vt 0x7F031B54); calls 0x7EEC40A3 (vtable slot 45 of AVPI class vt 0x7F031B54)	AVPI vtable 0x7F031B54 word 0x7F031BC8 + call graph	V	S

## 16e-graphics-avpi-index 0x7EE74066

0x7EE74066	53	C3D framework > class code	raises C3D error 2 (null argument); helper of 0x7EE73A66; under 0x7EE72CE6 (vtable slot +12 = copy of C3D class id 57; override chain: root/ancest) (2 levels up)	error-raise call with constant code + call graph	V	P

## 16e-graphics-avpi-index 0x7EE8541F

0x7EE8541F	37	C3D framework > class code > in the code block of class id 49 (by position, I)	helper of 0x7EE8556F (fini of C3D class id 49); calls 0x7EE7F27B (I: C3D string fini wrapper -> 0x7EE7F057)	call graph	V	P

