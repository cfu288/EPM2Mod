# Audit A12: random index rows, batch 2

## 16c-platform-function-index 0x7E465286

0x7E465286	69	soft-timer API (tmr_start/tmr_stop)	shared helper, 2 callers (soft-timer API (tmr_start/tmr_stop) 2)	call graph	V

## 16c-platform-function-index 0x7E579E7F

0x7E579E7F	192	WB white-balance/colour module	WB gain/colour getter for development; one of the row 0x7E579E7F / 0x7E579F3F / 0x7E57A028 / 0x7E57A0DC: gain and colour getters for development; service calls: prm data pointer(0xAA4A)	curated: 14b §3 + section 14b + callee signatures	V

## 16c-platform-function-index 0x7E514236

0x7E514236	49	MEC LCOM low layer	callback (no direct caller): address loaded at 0x7E5141CE in 0x7E5141B0, next call 0x7E512CE6; service calls: mec update/free	mov imm32 of the entry (callback rule) + callee signatures	V

## 16c-platform-function-index 0x7E46A6FA

0x7E46A6FA	337	SYSCLK clock/reset (0x98800000)	clk_gate(id 0-48 / 255, on): ref-counted SYSCLK gate 0x988000D0/D4 on, DC/E0 off; MMIO user: SYSCLK regs 0x988000D0, 0x988000D4, 0x988000DC, 0x988000E0; calls kernel services CPU lock, CPU unlock	curated: 13f §2.5 + MMIO constants 0x98000000-0x9AFFFFFF (13f §2.1) + kernel wrappers (callees)	V

## 16c-platform-function-index 0x7E535C4B

0x7E535C4B	291	lens module (tasks, command layer, shell, firmup, controller) > lens sync / sequence layer (error sub 0x0100)	uses strings “LPe/” | “LRe/” | “lsP/”; service calls: printf; shared helper, 10 callers (lens module (tasks, command layer, shell, firmup, controller) 10)	own strings + callee signatures + call graph	V

## 16d-core-play-overlay-index 0x7E958BEE

0x7E958BEE	394	`aud_dev_wm8946_output_path_spkout_l_control` (logs its own name); strings «aux1 =»	own string (bare)	V	S	Audio: bridge, control, WM8946 codec driver, DSP, FSC DMA, sequences, WAV/AC3 tools, AUD_*

## 16d-core-play-overlay-index 0x7E67D03C

0x7E67D03C	40	under api layer init: calls api_* module inits 0x7E675D99 (direct caller)	features+call graph	V	C	C camera API api_*.c (api_exec_start queue table)

## 16d-core-play-overlay-index 0x7E6C30BA

0x7E6C30BA	84	helper called by 0x7E6C30A9	call graph (unnamed callers)	V	C	touch panel (TOUCHPANEL 0x7E6BCF84, TP bootloader) and disp_sync

## 16d-core-play-overlay-index 0x7E62542E

0x7E62542E	52	uses strings «[cr]»; under `SC_RT` 0x7E5F8BE4 (2 levels up)	own strings (gist)	V	C	fcs/AF code tail (FCS_MOVIE/contrast AF helpers; setters 0x7E627E8D/96)

## 16d-core-play-overlay-index 0x7E6B6123

0x7E6B6123	133	work of case 16 of the switch in 0x7E6AEAD2 (the case arm calls it; table 0x7E7E20A0)	jump/hash table (jt.py)	V	S	DISPLAY task and display services

## 16d-core-play-overlay-index 0x7E71D010

0x7E71D010	16	wrapper: calls `debug print(a0 = str)` 0x7E4263E5 with a0=0x7E85564C	shape:wrapper	V	S	art filters and effects art_*.c (ART task 0x7E729E25)

## 16d-core-play-overlay-index 0x7F08DAE9

0x7F08DAE9	76	work of case 18 of the switch in 0x7F08D380 (the case arm calls it; table 0x7F0D510C); calls `put LE16` 0x7E507F72, `memcpy (fast)` 0x7E5081FA, case 18 of 0x7F08D49B 0x7F08DE97	jump/hash table (jt.py)	V	S	overlay B: TPC_LANG and TPC services (TPC DPST, TPC_OLPTPAPI) (I, position)

## 16d-core-play-overlay-index 0x7E93CC3E

0x7E93CC3E	293	calls `scheap alloc` 0x7E5072ED, `scheap free` 0x7E5072FB, `play_exif_search_tag` 0x7E941224; under `play_save_remain_num` 0x7E94AD8F (direct caller), `play_cube_resize_judge` 0x7E93D5D1 (2 levels up)	features+call graph	V	C	playback engine play_*.c / playbuff.c (PLAY_MAIN/IMAGE/LOAD/SOUND)

## 16d-core-play-overlay-index 0x7E6EE9BC

0x7E6EE9BC	222	section text: “`0x7E6EE9BC` (called from the QT/AVCHD encode loop 0x7E6EDB8D) does four things”	sec 04 line 61	I	S	movie mov*.c (MOV_* tasks, recorders, AVI/MOV writers, movie playback)

## 16d-core-play-overlay-index 0x7E632CA8

0x7E632CA8	3	empty stub: returns at once (no work)	shape:ret-only	V	S	cam_*.c files cam_aedrv … cam_frame_sync (03 §3, 14b)

## 16e-graphics-avpi-index 0x7EE624CE

0x7EE624CE	5	C3D framework > context/registry/stream	getter: returns (a0 +0); shared helper, 4 callers: 0x7EE75D3C (C3D root-level ctor: +12 name, +36 id, +40 = -1, +44 ctx), 0x7EE84E0C (own ctor level of C3D class id 24)	shape + call graph	V	S

## 16e-graphics-avpi-index 0x7EE5ACA6

0x7EE5ACA6	253	3D engine core > maths helpers (extent I)	sin(x), angle in turns; float computation: 15 soft-float ops (fsub×3, fmul×3, f2i×2, i2f×2)	curated: 14a 2.2 + soft-float callees (13a)	V	S

## 16e-graphics-avpi-index 0x7EE9E0FC

0x7EE9E0FC	92	AVPI > plug-ins	AVPI result codes 0xAA000103, 0xAA000104; helper of 0x7EE9DB19; under 0x7EE9E4B7 (vtable slot 2 of AVPI class vt 0x7F02FD10 type 0x0C02) (2 levels up)	error constants + call graph	V	P

## 16e-graphics-avpi-index 0x7EE4FB26

0x7EE4FB26	1058	3D engine core > type modules	helper of 0x7EE6A286; calls 0x7EE31766 (GL back end: fog state), 0x7EE31E10 (GL back end: matrix load), 0x7EE4CCA0 (field init: u16 +504 = 0, u8 +512 = 0)	call graph	V	P

## 16e-graphics-avpi-index 0x7EE4245C

0x7EE4245C	224	3D engine core > type modules	float computation: 6 soft-float ops (fcmp×5, fmul×1); helper of 0x7EE4253C; calls 0x7EE54E83 (set a 4x4 float matrix to identity and its flag bytes +64..+66 = 1)	soft-float callees (13a) + call graph	V	P

## 16e-graphics-avpi-index 0x7EE68013

0x7EE68013	28	C3D framework > class code	setter: u8 +32 = d0, u8 +33 = d0 (NULL-checked; range check against 0, 1); helper of 0x7EE67A5F; under 0x7EE81ECF (vtable slot +56 of C3D class id 50) (2 levels up)	shape + call graph	V	S

## 16e-graphics-avpi-index 0x7EE9E72A

0x7EE9E72A	26	AVPI > plug-ins	shared helper, 2 callers	call graph	V	C

## 16e-graphics-avpi-index 0x7EEB6A8D

0x7EEB6A8D	43	AVPI > plug-ins	vtable slot 3 (+12) of AVPI class vt 0x7F0311DC (Audio Decode Plug-in group, by position); virtual-call stub: calls slot +12 of the vtable of the object	AVPI vtable 0x7F0311DC word 0x7F0311E8 + shape	V	S

## 16e-graphics-avpi-index 0x7EE9E785

0x7EE9E785	103	AVPI > plug-ins	ctor (stores the vtable) of AVPI class vt 0x7F02FD38 (Audio Encode Plug-in group, by position); AVPI result codes 0xCA000003; uses memcpy	AVPI vtable 0x7F02FD38 loaded by code + error constants + runtime callees (13a, 14a)	V	S

## 16e-graphics-avpi-index 0x7EE77579

0x7EE77579	19	C3D framework > class code	wrapper: calls 0x7EE8EDDD; shared helper, 2 callers	shape + call graph	V	P

