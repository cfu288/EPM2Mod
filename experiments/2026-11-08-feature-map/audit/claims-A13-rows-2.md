# Audit A13: random index rows, batch 2 (5 per index)

## 16a-app-function-index 0x7E97119E

0x7E97119E	22	event 11981 isTypeOf	ev-isTypeOf	V

## 16a-app-function-index 0x7EA3C09F

0x7EA3C09F	6	CapBlc_BlurringCorrection setter (+4,this) = arg	getter-setter	V

## 16a-app-function-index 0x7EB6C7BA

0x7EB6C7BA	23	CmpPSou_PlaySoundComponent method: calls 0x7EB6C7D1 (CmpPSou_PlaySoundComponent sets field +208 = 1 [vt...); calls 0x7EA7CE74; calls 0x7EB6C842 (forwarder -> 0x7EB6C84A); called by 0x7EB6CCDD (CmpPSou_PlaySoundComponent method: [via 0x7EB6CC31: popNullConfig]; [v...)	g:callers	I

## 16a-app-function-index 0x7EBA3698

0x7EBA3698	15	Dev USB communication (range) probably an object ctor: stores vt 0x7EC91760 at +0 after base ctor 0x7EBA34BB (Dev USB communication zeroes fields +4,+8 of this )	object-ctor	I

## 16a-app-function-index 0x7EB9FCC6

0x7EB9FCC6	18	Ctg category method: calls 0x7EBA0247 (forwarder -> 0x7EBA024F); vcalls this->vt+208; called by 0x7EB9F826 (Ctg category transition step: exit (0x7EB9F81E); notify list +148 then...)	g:vcall+callers	I

## 16b-gui-function-index 0x7EDBD20E

0x7EDBD20E	54	Ss handler → stay; on: SS_PLAY_SINGLE 30 ZOOM_PREV_NEXT on 0x9008 KEY_LEFT_ON; calls (itself or in callees): PlaySingleFrame::moveCurrent	ss	V

## 16b-gui-function-index 0x7ED33DA8

0x7ED33DA8	1786	helper with 3 callers, e.g. 0x7ED31C9B (slanted-edge polygon fill)	caller	I

## 16b-gui-function-index 0x7EDFF150

0x7EDFF150	33	menu-page getter/creator for page(s) 8 (openPage functor case); list-page factory for list id(s) 8 (registry 0x7EFE180C); creator: new 1744 B, ctor 0x7EDFF12F (page class (pages 8)); in page class (pages 8) code	openpage,listreg,shape	V

## 16b-gui-function-index 0x7EE014AC

0x7EE014AC	33	menu-page getter/creator for page(s) 552-556 (openPage functor case); list-page factory for list id(s) 552-556 (registry 0x7EFE180C); creator: new 1748 B, ctor 0x7EE0148B (page class (pages 552,553,554,555…)); in page class (pages 552,553,554,555…) code	openpage,listreg,shape	V

## 16b-gui-function-index 0x7EDB791A

0x7EDB791A	800	Ss handler → returns a state computed in the handler (calls play controller , 0x7ED09135, 0x7ED01A03); on: SS_PLAY_SINGLE 31 IMAGE_PREV_NEXT on 0x9A01 GUI_END_PLAY_SINGLE_DISPLAY; calls (itself or in Ss callees): getSetting(27), PlayCommon::getImageType, PlayCommon::getStillInfo, PlaySingleFrame::getAspectFrame, PlayCommon::getNumber, PlaySingleFrame::updateImageSync; via 0x7ED09135: getSetting(27), getSetting(253) …	ss	V

## 16c-platform-function-index 0x7E601ECF

0x7E601ECF	108	AF (contrast AF / FCS_MOVIE / fcs shell)	probably C-AF re-init: work+6=0x1000, 0x7E623591, 0x6054C15C=0x2706, 0x6054C15E=1, lens sync 0x7E60FEFF(4,0), resets 0x7E5F9ABA/0x7E5F9A52/0x7E623A75/0x7E5FAEED/0x7E5FB2EB/0x7E5FEEC2, wob+1300=0	D5 read (af2): code	I

## 16c-platform-function-index 0x7E59F4A8

0x7E59F4A8	66	TAKE sequencer states and handlers	shared helper, 3 callers (TAKE sequencer states and handlers 3)	call graph	V

## 16c-platform-function-index 0x7E5BA1FE

0x7E5BA1FE	281	FAT file system (incl. exFAT format)	exFAT FAT writer (once per FAT copy); helper of 0x7E5B9DD7 (exFAT format sequence) (only caller)	curated: 14b §6 + call graph	V

## 16c-platform-function-index 0x7E533D12

0x7E533D12	37	lens module (tasks, command layer, shell, firmup, controller) > lens memory pool	helper of 0x7E533B5B (only caller), under 0x7E533AD2 (lens pool allocator core (errors 0x14009001 / 0x14009004))	call graph	V

## 16c-platform-function-index 0x7E54D4C5

0x7E54D4C5	10	IMG image-job library	wrapper: calls 0x7E5064E8 (debug print %s %s (2)); shared helper, 2 callers (IMG image-job library 2); e.g. 0x7E56DA08 (YC2 Recview RGB gamma (checks R=G=B))	shape: thunk (one call) + call graph	V

## 16d-core-play-overlay-index 0x7E92A8CE

0x7E92A8CE	57	probably: HCI Write_Authentication_Enable (0x0C20), 1 param bytes; waits Command_Complete; completion cb 0x7E92BA2E	15d tsv hci-cmd-builder	I (D6: demoted; V)	S	Blue SDK ME + SEC

## 16d-core-play-overlay-index 0x7E6DCF29

0x7E6DCF29	32	under `MOV_TASK task` 0x7E6C33B5 (3 levels up)	features+call graph	V	C	movie mov*.c (MOV_* tasks, recorders, AVI/MOV writers, movie playback)

## 16d-core-play-overlay-index 0x7E690F4B

0x7E690F4B	188	probably: face-table selector: mode 1 (clip) returns tables 0x605A6684/0x605A66AA and converts the clip offset (face_clip_x/y, ÷4608×640, ÷3456×480); else tables 0x605A6638/0x605A665E, offset 0; stores the HS grid params in AE work +780..+786	D5 exp decode (exp/hand_exp.tsv): code + strings	I (D6: demoted; V)	S	EXP_MOVIE `exp` module (live-view/movie AE)

## 16d-core-play-overlay-index 0x7E94FB41

0x7E94FB41	52	probably a `aud ld_clear` shell subcommand handler (it is called after a string compare with «ld_clear» in 0x7E94F73A; the full command path is not traced); entry «[PLAY]clear memory data(top address = M_SOUNDWORKBASE)» of {fn,name} table 0x7EBBEC80	shell decode (shells.py)	I	S	Audio: bridge, control, WM8946 codec driver, DSP, FSC DMA, sequences, WAV/AC3 tools, AUD_*

## 16d-core-play-overlay-index 0x7E63DAD9

0x7E63DAD9	19	function passed to the imgdev queue engine 0x7E63E8ED (I: completion callback); registered by 0x7E63DAA3; callback/pointer: address loaded as an immediate by 0x7E63DAA3	callback by consumer (D5: code immediate passed to a known API)	I	S	imgdev driver: per-command sequencers, IMGDEV_DRIVER dump 0x7E63E4B2, queue engine 0x7E63E

## 16e-graphics-avpi-index 0x7EE54E83

0x7EE54E83	87	3D engine core > maths helpers (extent I)	set a 4x4 float matrix to identity (1.0f on the diagonal) and its flag bytes +64..+66 = 1 (32 callers); shared helper, 32 callers	curated: D5 read + call graph	V	S

## 16e-graphics-avpi-index 0x7EE534DD

0x7EE534DD	76	3D engine core > type modules	shared helper, 2 callers	call graph	V	C

## 16e-graphics-avpi-index 0x7EE944C6

0x7EE944C6	6	AVPI > framework classes	vtable slot 1 (+4) = GetTypeId → 0x0B04 of AVPI class vt 0x7F02FB20 type 0x0B04; returns the constant 0xB04	AVPI vtable 0x7F02FB20 word 0x7F02FB24 + shape	V	S

## 16e-graphics-avpi-index 0x7EE6DEAF

0x7EE6DEAF	39	C3D framework > class code > in the code block of class id 43 (by position, I)	own vtable fill of C3D class id 43 (60-B instance, vt16); helper of 0x7EE6DF4D (vtinit of C3D class id 43: chain 0x7EE75DA2 → 0x7EE6EADF → 0x7EE6DEAF)	C3D ctor/vtinit chains + call graph	V	S

## 16e-graphics-avpi-index 0x7EEC46D8

0x7EEC46D8	210	AVPI > SCA session control	AVPI result codes 0x80000001, 0x80000003, 0x80000008; helper of 0x7EEC3F73 (vtable slot 25 of AVPI class vt 0x7F031B54)	error constants + call graph	V	P

