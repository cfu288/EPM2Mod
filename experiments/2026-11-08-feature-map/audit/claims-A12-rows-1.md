# Audit A12: random index rows, batch 1

## 16a-app-function-index 0x7EA3DCBD

0x7EA3DCBD	59	CapFls_Flash getInstance (singleton RAM 0x602B3020, returns iface +520)	getInstance	V

## 16a-app-function-index 0x7EA9E53A

0x7EA9E53A	8	CmpCst_Communication forwarder -> 0x7EA9E542 [target role: CmpCst_Communication state 10 entry (+404/+172): "disconnect"]	forwarder+tgt	V

## 16a-app-function-index 0x7EAEFD9E

0x7EAEFD9E	75	observer update() (slot 0 of 0x7EC696E4): builds 7080 and GENs it to target +20 [Com_ observer member]	obs-update	V

## 16a-app-function-index 0x7E9CDE02

0x7E9CDE02	24	code in OlyApi interface classes range, class not proven (callers only in sdk debug shell): schedule timeout (delay in register); vcalls +?->vt+48; called by 0x7E9BBE5B (sdk api handler q09 scStrncmp)	g:vcall+callers	I

## 16a-app-function-index 0x7EAE6368

0x7EAE6368	147	CmpETri_EditTrimmingComponent state 57 entry (+1124/+212): builds 12067 evTraCmp_NextState; GEN to self; "CmpETri_EditTrimmingComponent::single_mode_start#"	state-entry	V

## 16a-app-function-index 0x7E9C15AC

0x7E9C15AC	147	OlyApi CustomPrint::trimmingMode (API id 0x050313); vt word 0x7EC0EA38	olyapi-method	V

## 16a-app-function-index 0x7E96A475

0x7E96A475	9	code in TraShareTakeStatus range, class not proven (callers only in CmpSqp_SequencePartsBase): getter of RAM global 0x602B0D9C	getter-setter	V

## 16a-app-function-index 0x7EA427D3

0x7EA427D3	8	CapMod_ModeInformation forwarder -> 0x7EA427DB [target role: CapMod_ModeInformation state 8 entry (+252/+212): state trace; "ended"]	forwarder+tgt	V

## 16a-app-function-index 0x7EA3610D

0x7EA3610D	11	CapTak_Take forwarder [vt slot 32 of CapTak_Take] -> 0x7EA361F0 [target role: CapTak_Take forwarder -> 0x7EA361F8 [target role: CapTak_Take state 3 entry (+208/+212): state trace]]	forwarder+tgt	V

## 16a-app-function-index 0x7EB0493B

0x7EB0493B	63	CmpPCal_PlayCalendarComponent state 39 handler: 12067 evTraCmp_NextState -> state 49; else parent 0x7EB021F2	handler	V

## 16b-gui-function-index 0x7ED68791

0x7ED68791	1473	panel 13 (type 0x600D) vt slot 91 (+364) = post-create init; does: setVisible, DM get block 3, DM get block ?, DM get block 2, DM get block 37, DM get block 31, DM get block 34	vt,args	V

## 16b-gui-function-index 0x7ED0652F

0x7ED0652F	448	post GM 0x9A40 , read-modify-write of DM block 80, read-modify-write of DM block 81 … (inputs: PlayLightBox::getEnlargeInfo, PlayLightBox::getNumber, PlayCommon::getStillInfo); logs 'getEnlargeInfo result=%d', 'getNumber() base=%d, current=%d'; method of CPlayLightBox (singleton RAM 0x602B605C); does: applyLongPressProfile, DM get block …	synth,str,args	V

## 16b-gui-function-index 0x7ED04177

0x7ED04177	64	reads PlayCommon::getSelectPicNumber; logs 'OlyApiPlayCommon::getInterface()->getSel'; method of CPlayIndex (singleton RAM 0x602B6054, 3,300 B); does: PlayCommon::getSelectPicNumber	synth,str,args	V

## 16b-gui-function-index 0x7EDDBCA2

0x7EDDBCA2	6	getter of field +12 (movhu); in 15a class row "return-to (SS, state)" singleton: getInstance 0x7EDDBC06 (RAM 0x602BD	shape	V

## 16b-gui-function-index 0x7ED719EB

0x7ED719EB	35	code: calls 0x7ED6F7D9; stores 0 (u8) to [(2018 + a0)+3]; calls 0x7ED6587F; returns result of 0x7ED6587F; short wrapper → 0x7ED6F7D9 then 0x7ED6587F; in panel 29 (type 0x601C) code; via 0x7ED6587F: setVisible, setU16Prop8013	code,shape,callee	V

## 16b-gui-function-index 0x7ED7EB2D

0x7ED7EB2D	117	private method (in unnumbered panel class type 0x6061 code); called by 0x7ED7EA53 (unnumbered panel class type 0x6061 vt slot 91 [+364] = post-create init), 0x7ED7EAFA; via 0x7ED7EBA2: setVisible; via 0x7ED7EC12: setVisible	range,callee	I

## 16b-gui-function-index 0x7ED69718

0x7ED69718	465	updates child widgets (visibility, 0x8013 value); private method (in panel 13 (type 0x600D) code); called by 0x7ED68791, 0x7ED68D52; does: setVisible, setU16Prop8013	synth,range,args	I

## 16b-gui-function-index 0x7ED62F4C

0x7ED62F4C	409	updates child widgets (visibility, position); private method (in panel 10 (type 0x600A) code); called by 0x7ED626F3; does: setVisible, moveTo	synth,range,args	I

## 16b-gui-function-index 0x7EDDF19D

0x7EDDF19D	32	GuiTouch action handler: touch action 8 of panel 10 (type 0x600a)	touch	V

## 16b-gui-function-index CA ShootingLvMagnify[0x5A05]/0x0100000F

CA ShootingLvMagnify[0x5A05]/0x0100000F	-	CA ShootingLvMagnify state 0x5A05 on 0x0100000F OLY_RELEASE_LEFT_KEY → handler 0x7ECDC0D6 (releaseKeyZoomScroll); same state	ca-table	V

## 16c-platform-function-index 0x7E507325

0x7E507325	14	sc library (shell, SC_TTIMER, scheap, utils, RTC/calendar)	scheap large alloc (16 KB block) wrapper (14-B: mov pool,a0/a1; call core); wrapper: calls 0x7E507395 (scheap alloc core (pool by pointer, lock 0x7E436593)) with a0=fn 0x7E507450 (logs “scheap_large_alloc”)	curated: 14b §2 + shape: thunk (one call)	V

## 16c-platform-function-index 0x7E53BBB3

0x7E53BBB3	225	BC body-stabiliser controller > BC command layer (classes 0-3)	service calls: scheap small alloc; scheap small free; helper of 0x7E53BAF0 (only caller), under 0x7E53D96D (BC_MAIN task: 16-B Oimf messages, code msg+8 (0-34) via jump)	callee signatures + call graph	V

## 16c-platform-function-index 0x7E5ADE37

0x7E5ADE37	86	DCF (folder/file numbering, scan)	FAT request: set parent-dir location (+76..) from root entry record n (0 DCIM, 1 MISC, 2 PARAMDT) of drive via 0x7E5B4527/0x7E5B453E; n>2 -> zeros	D5 read (dcf): calls 0x7E5B6463, 0x7E5B4527, 0x7E5B453E	V

## 16c-platform-function-index 0x7E464ADB

0x7E464ADB	3	I/O expander IOE/IOEC (SIO ch3)	empty function (`retf`, does nothing); helper of 0x7E4649E8 (IOE class register init part 1 (devid) (only caller)	shape: lone return + call graph	V

## 16c-platform-function-index 0x7E5C8D48

0x7E5C8D48	60	EYEFI requests, AVCHD paths, EYEFI/FILECLBK tasks, file shells, FILEFGND, dcfnum	DCF path parse (a0 '/DCIM/100OLYMP/PA010001.JPG', len >= 25): folder number from +8, file number from +17; returns 0 or 0xFFFF (dcf_get_index_from_path helper); helper of 0x7E5AFB62 (dcf_get_index_from_path) (only caller)	D5 read (eyefi): strlen >= 25, 0x7E5C8CD3, 0x7E5C8C4B + call graph	V

