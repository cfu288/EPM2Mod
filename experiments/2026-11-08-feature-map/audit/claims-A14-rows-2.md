# Audit A14: random index rows, batch 2 (5 per index)

## 16a-app-function-index 0x7EB2C5C0

0x7EB2C5C0	249	Cmp_PlayIndexComponentBase rootState_dispatchEvent (slot 33) on +212: 28 states (3,5,6,7,8,9,10,12,14,15,17,19...)	dispatcher	V

## 16a-app-function-index 0x7EA460DF

0x7EA460DF	15	event 4425 dtor	ev-vtslot	V

## 16a-app-function-index 0x7E9761A5

0x7E9761A5	15	event 12866 dtor	ev-vtslot	V

## 16a-app-function-index 0x7E9C1966

0x7E9C1966	99	OlyApi CustomPrint::makePreview (API id 0x050322); vt word 0x7EC0EA44	olyapi-method	V

## 16a-app-function-index 0x7E9E7A04

0x7E9E7A04	60	code in OlyHfwUserSettingManager range, class not proven (callers only in Tra request base): pointer-collection remove(); called by 0x7E999F84 (Tra request base method: getInstance 0x7E9E762F (RAM 0x602B286C); [via...)	g:callers	I

## 16b-gui-function-index 0x7ECDBA83

0x7ECDBA83	133	CA ShootingLvMagnify state 0x5A0C on 0x01000023 OLY_RELEASE_MOVIE_KEY → table next: same state; the handler code (with callees that receive ctx) contains stores ctx+92 = 0x5000 in callee 0x7ECD5B04 / 0x5003 in callee 0x7ECD75CE / 0x5108 in callee 0x7ECD5270 / computed in callee 0x7ECD5270; whether they run on these events is not checked …; its code contains stores sub-event request ctx+76 = 0x0900001F …	ca	V

## 16b-gui-function-index 0x7ED3F616

0x7ED3F616	318	panel 54 (type 0x6026 GCPnl_Calender) vt slot 91 (+364) = post-create init; does: DM get block 54, DM get block 97	vt,args	V

## 16b-gui-function-index 0x7ED61C48

0x7ED61C48	43	calls widget setters (visibility); private method (in panel 10 (type 0x600A) code); called by 0x7ED60A95, 0x7ED60F27; does: setVisible	synth,range,args	I

## 16b-gui-function-index 0x7EDA1A72

0x7EDA1A72	105	Ss handler → stay; on: SS_DPS 4 on 0x9032 ST_CHANGE_MAIN_DIAL; calls (itself or in callees): getSetting(170), getSetting(309), self-post 0x9004 KEY_UP_ON	ss	V

## 16b-gui-function-index 0x7EDF517D

0x7EDF517D	24	code: calls 0x7EBA62E3; sets a0+20 = result of 0x7EBA62E3; calls 0x7EDF5195; short wrapper → 0x7EBA62E3 then 0x7EDF5195; via 0x7EDF5195: SettingController::getSetting, ModeCheck::canExecute, SettingController::canSettingValue	code,shape,callee	V

## 16c-platform-function-index 0x7E5CA326

0x7E5CA326	213	file wrapper / VFS	fflush(FILE a0): writes the pending combine buffer, updates the dir entry (size, times, cluster; op mask 0x74) by path walk, clears dirty, FAT flush 0x7E5C9605	D5 read (dpof): read	V

## 16c-platform-function-index 0x7E538797

0x7E538797	34	lens module (tasks, command layer, shell, firmup, controller)	when live lens record 0 exists (0x7E51FD37(0)): u32 0x60503974 = 2 * u16 record0[628 + 16 * byte record0+8]; else nothing; branch summary: calls 0x7E51FD37 (lens record getter gated by the protocol flags) with d0 = 0; if ret(0x7E51FD37) == 0: [returns] else: [u32[0x60503974] = (u16[ret(0x7E51FD37)+628+((u8[ret(0x7E51FD37)+8])<<4)]+u16[ret(0x7E51FD37)+628+((u8[ret(0x7E51FD37)+8])<<4)])]	D7 read (lensA): clr d0; call 0x7E51FD37; movbu (8,a0); add 628,a0; asl 4; movhu (d0,a0); add d0,d0; mov d0,(0x60503974) + branch summary (1-3 forward branches)	V

## 16c-platform-function-index 0x7E522484

0x7E522484	9	lens module (tasks, command layer, shell, firmup, controller)	global setter: stores u16 d0 to RAM 0x604F901A; leaf: u16[0x604F901A] = d0	shape: mov reg,(abs); retf + leaf summary (straight-line, no call)	V

## 16c-platform-function-index 0x7E5CC9C8

0x7E5CC9C8	22	SD host driver (0x99000000)	branch summary: calls 0x7E46144E with d0 = 190; if (u16)ret(0x7E46144E) == 0: [returns d0 = 0] else: [returns d0 = 1]; helper of 0x7E5CE33A (only caller)	branch summary (1-3 forward branches) + call graph	V

## 16c-platform-function-index 0x7E506C15

0x7E506C15	6	firmware-package helpers	field getter: returns u32 at +8 of a0; leaf: returns d0 = u32[a0+8]	shape: mov (off,an); retf + leaf summary (straight-line, no call)	V

## 16d-core-play-overlay-index 0x7E6DD153

0x7E6DD153	31	initialiser/setter: writes 4 globals 0x605B15A8, 0x605B15AA, 0x605B15AC …	shape:multistore	V	S	movie mov*.c (MOV_* tasks, recorders, AVI/MOV writers, movie playback)

## 16d-core-play-overlay-index 0x7E71C5B4

0x7E71C5B4	128	`art_chk_effect_monotorn` (logs its own name)	own string (io)	V	S	art filters and effects art_*.c (ART task 0x7E729E25)

## 16d-core-play-overlay-index 0x7E6C1BF6

0x7E6C1BF6	60	uses strings «[disp_sync]DISP_UPDATE_SCREEN_OSD err!»; calls `debug print str + hex value` 0x7E50652F; under `update_osd` 0x7E6BEA63 (direct caller), `sync` shell 0x7E6C1579 (2 levels up)	own strings (gist)	V	C	touch panel (TOUCHPANEL 0x7E6BCF84, TP bootloader) and disp_sync

## 16d-core-play-overlay-index 0x7E91D6B2

0x7E91D6B2	87	probably: L2CAP_DisconnectReq(cid d0): for a channel in states 2..5 with a remote CID, sends Disconnection Request (0x7E91D960); 1 bad cid, 19 busy	D5 BT decode (bt/hand_bt.tsv): code	I (D6: demoted; V)	S	L2CAP

## 16d-core-play-overlay-index 0x7E943DDE

0x7E943DDE	1285	`play_gpu_draw` (name from the sections)	section name	V	S	play_gpu.c

## 16e-graphics-avpi-index 0x7EE8D400

0x7EE8D400	18	C3D framework > class code	per-level copy step of the C3D slot +12 (copy) override chain (step 3 of 4/3 of 5/3 of 6) in 0x7EE80CAD, 0x7EE81D1B (vtable slot +12 = copy of C3D class id 29; override chain: root/ancest) and 19 more; the chain stops unless it returns 1	C3D override-chain step (D7: called as a step of a bool chain whose first call is a root slot method)	V	S

## 16e-graphics-avpi-index 0x7EEA183C

0x7EEA183C	89	AVPI > plug-ins > Audio Source Plug-in code (by position, I)	plug-in interface slot 52 (+208) of Audio Source Plug-in main class (vt 0x7F02FF28); strings: «CAvpiAsoAudioSource.cpp»; AVPI result codes 0xAB010003	AVPI vtable 0x7F02FF28 word 0x7F02FFF8 + own strings + error constants	V	S

## 16e-graphics-avpi-index 0x7EE8E111

0x7EE8E111	18	C3D framework > class code > in the code block of class id 16 (by position, I)	own-level write body: the last step of the C3D slot +4 (write) override chain in 0x7EE8DE33 (vtable slot +4 = write of C3D class id 16; override chain: root/ancest); the chain stops unless it returns 1; calls 0x7EE8E04C (calls vtable slots of the argument a1: +12 ×1	C3D override-chain step (D7: called as a step of a bool chain whose first call is a root slot method) + call graph	V	S

## 16e-graphics-avpi-index 0x7EE680A0

0x7EE680A0	29	C3D framework > class code	helper of 0x7EE681B5; under 0x7EE66E14 (vtable slot +0 = serialised size of C3D class id 1) (5 levels up)	call graph	V	P

## 16e-graphics-avpi-index 0x7EE6EA18

0x7EE6EA18	46	C3D framework > class code	vtinit of C3D class id 44 (84-B instance, vt16): chain 0x7EE75DA2 → 0x7EE6EADF → 0x7EE6E900; calls 0x7EE75DA2 (C3D root vtinit), 0x7EE6EADF (C3D base-level vtable fill shared by class ids 43, 44), 0x7EE6E900 (own vtable fill of C3D class id 44)	C3D registry 0x7EE64322 + call graph	V	S

