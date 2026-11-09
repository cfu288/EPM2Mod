# 15d — Protocol stacks (Blue SDK, HDMI/CEC, DPS) and platform gaps: function-level indexes

Round D3 (2026-11-09). Scope:
- the Bluetooth stack interior (section 05 said only "stack");
- the string-less HDMI EDID/CEC and display-controller helpers in 0x7E6A–0x7E6B;
- the DPS (PictBridge) engine in overlay A;
- the unnamed runs of 0x7E421020–0x7E520000.

The function-level indexes are in **`15d-protocols-platform.tsv`** (columns `addr_or_id`, `kind`, `role`, `evidence`, `V/I`). This file gives the bounds, the components, the patterns for classifying a function, and the corrections.

Labels: **V** = read in code or bytes. **I** = inferred. Register *names* for the HDMI transmitter come from the public ADI ADV7511-family register map, not from strings, so they are always I, while the register *numbers* are V. Scratch: `$S/d3/proto/`.

## 1. Area and boundaries

| Range | Component | Basis |
|---|---|---|
| 0x7E915A1B–0x7E91962B | Blue SDK part 1: stack init 0x7E915A1B, event manager/timers 0x7E915AAE–0x7E915C68, profile layer 0x7E915D0C–0x7E917A3F, **HCI layer 0x7E917AFE–0x7E91962B** | V call edges, RAM pages; names I |
| 0x7E91962C–0x7E91D29E | Olympus iAP (BT_Open, cp_*, BTIAP, IDPS); getters 0x7E91D279/0x7E91D289 belong to it | V strings |
| 0x7E91D29F–0x7E937CDD | Blue SDK part 2: L2CAP → debug Report → Olympus test client → ME/SEC → BT API wrappers → OBEX → OS layer → radio manager → RFCOMM → RX buffers → SDP → SPP → utilities | V bounds (layer edges below) |
| 0x7E6A9323–0x7E6AD7FF | ADI HDMI transmitter driver `[HDMI-DRV]` (EDID, video, audio, InfoFrames, power) | V register calls; I lower bound |
| 0x7E6AD80C–0x7E6AEA69 | ADI CEC library (`ADI_CEC`) | V register calls; bounds I |
| 0x7E6AEA6A–0x7E6B74xx | DISPLAY task and display services (section 08) | V strings |
| 0x7E6B749A–0x7E6B990E | display-controller (0x9A900000) ISR and register writers | V absolute operands |
| 0x7E6B9932–0x7E6BAFFF | HDMI task, CEC poll, I2C transports over SIO ch2/ch3 | V |
| 0x7E6BB06E–0x7E6BCD96 | second transmitter on SIO ch3 (`outevf_tmds`) | V regs; I role |
| 0x7F05E9CE–0x7F0645C0 | DPS engine in overlay A (not 0x7F061020–0x7F068F9C) | V |

**The Bluetooth stack is not one block at 0x7E91D279.** The HCI layer that feeds the ME event dispatcher sits at 0x7E917AFE–0x7E91962B. The caller chain is 0x7E924E3A ← 0x7E924D10 ← 0x7E917D1E/0x7E9180E4/0x7E918121/0x7E91820A/0x7E9189C4/0x7E918BE8, and the command sender 0x7E925704 sends through 0x7E917F02 (V). The Olympus iAP code is linked between the HCI layer and L2CAP.

## 2. Blue SDK Bluetooth stack

### 2.1 Layers (interior bounds)

The bounds come from the RAM pages each function touches and from the inter-layer call matrix (`$S/d3/proto/ramprof.txt`).

| Range | Layer | RAM | Key entries; evidence |
|---|---|---|---|
| 0x7E91D29F–0x7E923747 | **L2CAP** | 0x7DAE4xxx | PSM registration 0x7E91D29F (I). ERTM state handlers 0x7E91E215/0x7E91E75F/0x7E91EC0E (fwmap merged them; coverage C3). Signalling length check 0x7E9234DC: codes 1..11, table 0x7EBB1F08, code 8 = Echo (V). MTU constant 672 (V). RFCOMM calls it 19×, SDP 21× (V) |
| 0x7E923748–0x7E923927 | debug `Report` | — | 0x7E923748 (56 callers) → formatter 0x7E923769 → debug print 0x7E4263E5 (V) |
| 0x7E923928–0x7E924003 | Olympus test client | 0x602AE, 0x605D0–5 | `OLYMPUS BlueSDK a4`, BTAPL task 0x7E923FD2, demo-shell entries 0x7E923C93–0x7E923FFB (V) |
| 0x7E924004–0x7E925A48, 0x7E9266BE–0x7E92BF5D | **ME + SEC** (management entity, security) | 0x7DAC4xxx–0x7DAC5xxx | ME_Init 0x7E924004. Op scheduler 0x7E92412E. Event dispatcher 0x7E924E3A. Command sender 0x7E925704. HCI init 0x7E925727. Link records 0x7E9275C6–0x7E9276AC. SEC 0x7E92A181–0x7E92BF5D (`SecReportAuthenticateResult`) (V) |
| 0x7E925A49–0x7E926692 | BT API wrappers (Olympus or SDK sample) | 0x605D6xxx | BT init 0x7E925A49; deinit 0x7E925E9C; wait 0x7E926118 (OlyEvWt); signal 0x7E926146 (OlyEvSt); `BT_SetSecurity` 0x7E925B4F/0x7E926620 (V edges; role I) |
| 0x7E92C029–0x7E92E37A | **OBEX core** | 0x7DAF2xxx | Client: opcodes 0x80/0x81/0x82/0xFF, body headers 0x48/0x49. Server 0x7E92D432–0x7E92DC08: 0x85 SetPath, headers 0x46/0x4A/0xCB, responses 0x90/0xA0/0xC0/0xC4. Packet pool 0x7E92DD6A: 64 × 724 B (V constants) |
| 0x7E92E37B–0x7E92EC6B | OBEX transport over RFCOMM | 0x7DAE7xxx | API lock/unlock 0x7E92E37B/0x7E92E390 (33 callers in BT_CTRL). Server transport 0x7E92E5D6 (V) |
| 0x7E92EC6C–0x7E92F0FD | OPP/BIP application glue | 0x605D648C | Called by BT_CTRL 0x7E8FB30D–0x7E8FBEF7 (V edges; role I) |
| 0x7E92F0FE–0x7E92F66F | **OS layer** | — | The stack lock 0x7E92F4EC/0x7E92F57A, BTTIM 0x7E92F345, BTSTK 0x7E92F5F7, mem*, mutex and wake helpers (TSV) (V) |
| 0x7E92F68D–0x7E92FCBC | radio manager / HCI transport | 0x7DAD1xxx | Init 0x7E92F68D → HCI init 0x7E917AFE. It watches HCI_Reset 0x0C03 and the vendor command 0xFC18 (V constants; role I) |
| 0x7E92FCBD–0x7E933AED | **RFCOMM** | 0x7DAE5xxx | Frame types with P bit: 0xEF UIH (9×), 0x3F SABM (14×), 0x53 DISC (15×), 0x73 UA (7×), 0x1F DM (11×). SABM-state strings 0x7E93101B–0x7E9315FD; mux 0x7E931921; sessions 0x7DAE5C88 + i·1344 (V) |
| 0x7E933AEE–0x7E933C46 | HCI RX buffer pools | 0x7DAC5ACC | Init 0x7E933AEE (called from HCI init); free 0x7E933C06 (called from HCI RX) (V code; name I) |
| 0x7E933C47–0x7E936A46 | **SDP** client + server | 0x7DAE5xxx | Big-endian accessors (26 BE16 reads, 17 BE16 writes vs 0 LE). L2CAP callback 0x7E933E4B (events 1..10). SDP_AddRecord 0x7E934A5E: record {+8 = 9 attributes, +16 = CoD bits 0x100000} from BT_CTRL 0x7E8F96DC (V edges; names I) |
| 0x7E936A47–0x7E937BE1 | SPP (serial port) | 0x605D6xxx | Used by iAP: open 0x7E937022 ← BT_Open. BTEVU task 0x7E9375B4 (V edges; names I) |
| 0x7E937BE2–0x7E937CDD | utilities | — | BE16/BE32/LE16 get/put and list ops (TSV) (V) |

Layering, top to bottom (V call edges):
- DevBlu → api_cube → `[btc api]` → BT_CTRL (05);
- BT_CTRL → profile layer / OBEX / BT API, plus BTAPI glue 0x7E913984–0x7E9158FD → ME;
- RFCOMM → L2CAP → HCI (0x7E917F02 / 0x7E91917E) → radio manager → UART transport (0x7E912E84 in 05's patch/UART block).

iAP runs over SPP → RFCOMM. This answers 05's open question 4 for the transport: BT_Open → 0x7E937022 (V edge; "SPP" I).

### 2.2 HCI commands

All commands go through **`hci_send(opcode d0, len d1)` 0x7E925704**. It stores the opcode at 0x7DAC56CC and sets busy 0x7DAC571D = 1. The packet is 0x7DAC4B44, its parameters start at 0x7DAC4B4F, and it is sent by 0x7E917F02 (V).

**Builder pattern (V).** You can classify any builder by these instructions, in order:
1. `mov <cb>,d0; mov d0,(0x7DAC4C48)`: the completion callback (0x7E9248CC = Command Complete path; 0x7E924941 = Command Status path; 0x7E9258F2 init, 0x7E92BA2E security, 0x7E928124 role discovery).
2. `mov 14|15,d0; movbu d0,(0x7DAC4C4C)`: the event it waits for.
3. `mov (0x7DAC4B40),a0`: the current op.
4. The fields are stored with `put_le16` 0x7E937C3C at a0 = 2108443471 (0x7DAC4B4F) + k.
5. `mov opcode,d0; mov len,d1; call 0x7E925704`, then usually `call 0x7E925058`, which clears the pending command.

The TSV has **47 builder rows** (opcode, length and callback, all V):
- **Link control** 0x0401–0x0434 (Inquiry, Create Connection, Disconnect, accept/reject, link-key/PIN/passkey/confirm/OOB replies, authentication, encryption, remote name and features);
- **link policy** 0x0801 Hold, 0x0803 Sniff, 0x0804, 0x0805 Park, 0x0806, 0x080B Switch Role (0x7E9273A6–0x7E927576), 0x0809, 0x080D, 0x080F, 0x0811;
- **controller/baseband** 0x0C01–0x0C5B (event mask, local name, page timeout, scan enable/activity, IAC LAP, CoD, EIR 241 B, SSP mode, OOB, TX power);
- **informational** 0x1001/0x1003/0x1009; **testing** 0x1804 SSP debug mode.
- 0x7E9247FC passes a raw command through (opcode and length from op +32/+34).

**HCI init (0x7E925727, V;** step counter 0x7DAC4C67, jump table 0x7EBB4504**):** Write_Page_Timeout(0x2000) → Read_Page_Timeout → Set_Event_Mask → Read_Local_Version → Read_Local_Supported_Features → Read_BD_ADDR → Read_Inquiry_Mode → Read_Default_Erroneous_Data_Reporting (only if LMP feature bit 53) → Read_Inquiry_Response_TX_Power → Write_Simple_Pairing_Mode(1) (only if feature bit 51, SSP). The feature test is 0x7E92A144(bit). Section 05's Broadcom bring-up (Write_RAM/Launch_RAM, BD_ADDR, baud) happens before this, in BT_CTRL.

### 2.3 HCI event dispatcher 0x7E924E3A (V)

- `cmp 1..61`, then jump table 0x7EBB3C1C, index = event − 1.
- Handled events: 0x01, 0x02/0x22/0x2F (one inquiry-result handler 0x7E924A75 with flags d1/a1 = 0/0, 1/0, 1/1), 0x03–0x08, 0x0B, 0x12, 0x14–0x18, 0x1B (ignored), 0x1D, 0x20, 0x23, 0x2E, 0x30 (shares 0x7E92B0E9 with 0x08), 0x31–0x36, 0x38, 0x3B–0x3D. The TSV has one row per slot.
- **Default path** 0x7E924FB3: for 0x0E Command Complete (opcode at +1) and 0x0F Command Status (opcode at +2) it compares the opcode with the pending opcode 0x7DAC56CC and, on a match, calls the callback (0x7DAC4C48). Otherwise 0x7E92518F looks for a waiting op that matches the event (0x7E9250BB completes it); 0x0D QoS Setup / 0x21 Flow Spec Complete → 0x7E927D86; anything else returns 0.
- So 0x13 Number_Of_Completed_Packets never reaches ME through this table. It is handled in the HCI layer (I).

### 2.4 ME operations and link records (V)

- **Op scheduler 0x7E92412E.** It runs only when the ME is ready (0x7DAC4C65 = 1), no op is current, and no command is pending. It then pops the op queue 0x7DAC4A08 into curOp 0x7DAC4B40 and switches on **op type (op +8, 1..65)** through table 0x7EBB3B18. Each case stores a start function at 0x7DAC4C50 and runs it.
- The TSV maps each op type to its start function and HCI command. Examples: 1 Inquiry, 5 Create Connection, 8 Disconnect, 9–14 security, 19–24 Hold/Sniff/Exit Sniff/Park/Exit Park/Switch Role (0x7E926E88 is op 22 Park, not a mode chooser), 25 CoD, 26 raw command, 55/56 inquiry mode/EIR, 64/65 TX power and SSP debug mode.
- Several start functions sit 3–5 bytes before the fwmap function start: 0x7E926F43, 0x7E926FA1, 0x7E92700B, 0x7E924470, 0x7E9244E5, 0x7E924BD5, 0x7E92A56E. **The pointer value is the true entry.**
- **Link records at 0x7DAC4C68, stride 320.** All 3 loops (0x7E9275C6 find by BD_ADDR, 0x7E927600 allocate, 0x7E927681 find by handle) stop at `cmp 1`. So **there is exactly one record**: the stack supports one ACL link (V). The record starts with the op node, so for link commands curOp is the record. Fields:

| Offset | Field | Basis |
|---|---|---|
| +0 / +8 | op node / op type | the scheduler |
| +84 | BD_ADDR (6) | find-by-addr |
| +108 | link-handler list | MeCallLinkHandlers 0x7E9276AC |
| +128, +232, +244 | lists | allocator |
| +144 | HCI handle | find-by-handle; Park/Hold/Disconnect |
| +146 | in-use / state (0 = free) | allocator, free 0x7E927679 |
| +149 | disconnect reason | Disconnect 0x7E9272F6 |
| +150 | packet types, default 0xCC18 = DM1/DH1/DM3/DH3/DM5/DH5 | allocator; Create_Connection |
| +152 | packet types for Change_Connection_Packet_Type | 0x7E927058 |
| +188–+194 | mode/connect parameters: Hold/Park max/min intervals; Sniff max/min/attempt/timeout; for Create_Connection PSRM, reserved, clock offset, role switch | builders |
| +224 | → a 678-B record at 0x7DAC4E00 | allocator |

### 2.5 PENPAL on top

The PENPAL profile is the Olympus code above the stack (section 05): BT_CTRL 0x7E8F926F–0x7E9035A7 (OPP push, BIP, pairing), BTAPI glue 0x7E913984–0x7E9158FD (`CB_BtEvtHandle`, link-key store), iAP/ACP 0x7E91962C–0x7E91D29E and OBEX_ACP 0x7E937CDE–0x7E93BA6B. It reaches the stack through OBEX (BIP/OPP servers registered with SDP_AddRecord 0x7E934A5E), SPP (iAP `jp.co.olympus.acp`) and the ME API (pairing, security).

The **Olympus test client 0x7E923928–0x7E924003** is a vendor sample. It is reachable only from the demo shell and BTAPL (05).

## 3. HDMI transmitter, CEC and display controller

### 3.1 HDMI-DRV register pattern (V)

- **Field write 0x7E6AC903:** (dev d0, reg d1, mask a0, shift a1, value at sp+4). It reads and writes through the function pointers 0x605ABE70 (read) and 0x605ABE6C (write). It has 168 callers.
- **Field read 0x7E6AC8E6:** same arguments, 29 callers. Multi-byte read: 0x7E6AC943.
- **Device 0x72 = transmitter main map; 0x78 = CEC map.** The CEC map address is read from main register 0xE1, which fits the string `CEC Addr(0xE1)`. Device 0x70 is used only at reg 0xDF.
- **Classifying a function:** list its `(d0, d1)` pairs before calls to 0x7E6AC903/0x7E6AC8E6. The TSV gives the register set of every writer.

ADV7511-family names fit every register used (I): 0x41 power-down; 0x42 HPD/monitor sense; 0x94–0x97 interrupt enable/status; 0xC4/0xC8/0xC9 EDID segment/state/re-read; 0x15–0x18 input/output format and CSC; 0x40/0x44/0x4A/0x4B packet enable/update/AV mute; 0x55–0x61 AVI InfoFrame; 0x73–0x77 Audio InfoFrame; 0x0A–0x0D audio; 0xAF HDMI/DVI; 0x98/0x9C/0x9D/0xA2/0xA3/0xDE/0xE4/0xE5/0xE6/0xEB/0xBA = the fixed power-up set (0x7E6AD6D0).

### 3.2 EDID parse steps (V order, from call edges)

1. **Hot-plug / interrupt:** 0x7E6AC28C. It reads 0x96, 0x42, 0xC8 and 0xA1. Power-up path: 0x7E6AC5AB → 0x7E6AC803.
2. **Read request:** EDID state poll 0x7E6AC56F (0xC8) → buffer and request 0x7E6A93E5 (`[hdmi]get heap error`) → segment request 0x7E6AC4DF (0xC4, 0xC9).
3. **Segment parser 0x7E6AC127**, per 128-byte block:
   - block 0 → **base-block parser 0x7E6AB32D**: `memcmp(block, 00 FF FF FF FF FF FF 00, 8)` against 0x7E7E1B0D (bytes checked), then the checksum;
   - block map → 0x7E6A977B;
   - CEA extension → **0x7E6AA7CB** (checksum, data-block tags 1–4, `invalid tag in cea data block`).
4. **Shared decoders:** getbits 0x7E6AC006 (213 callers); bit-field decoder 0x7E6A9821; timing decoder 0x7E6A99B6 (3,605 B, soft-float) (I: detailed timings).
5. **Result records:** reset 0x7E6AC02B runs the initialisers 0x7E6AB93D–0x7E6ABB69 and stores the pointers in 0x605AB3DC–0x605AB620.
6. **Mode programming:** colour space 0x7E6ACADC (`Problem selecting colorspace`); aspect 0x7E6ACED5; input format 0x7E6ACF45; audio 0x7E6ACFC2/0x7E6AD16B; AVI / Audio InfoFrames 0x7E6AD2F2 / 0x7E6AD4B1; AV mute/packets 0x7E6AD266/0x7E6AD2AC; TMDS gate 0x7E6AD201; HDMI/DVI 0x7E6A951A; power-down 0x7E6AC9F4.

### 3.3 CEC (V register calls; meaning I)

- The ADI CEC library 0x7E6AD80C–0x7E6AEA69 (`ADI_CEC` 0x7E6AE2FF) accesses the CEC map 0x78 through 0x7E6B9B19 (write) and 0x7E6B9B2A (read). Those call the SIO ch2 I2C pair 0x7E6BA39B/0x7E6BA448.
- Init 0x7E6ADE80 reads 0xE2/0xE1, then CEC map 0x4B/0x4E/0x50/0x51/0x6E/0x70/0x71.
- Main-map CEC interrupts: 0x95 (enable), 0x97 (status).
- CEC map registers: TX frame 0x10/0x11 (0x7E6AE0CE, 0x7E6AE117), TX status 0x12 (0x7E6AE033), logical address 0x4B (0x7E6AE064), RX enable 0x26/0x4A (0x7E6AE603).
- The poll `CEC_RW` 0x7E6B9B3B reads 0xE2 first. The CEC opcode table was not decoded (open question).

### 3.4 I2C transports and the second transmitter (V)

| Transport | SIO channel | Bus select | Read / write / field helpers |
|---|---|---|---|
| HDMI | ch2 (wait 0x7E6BA554) | 0x7E6BAF45(0) | read 0x7E6BA39B / write 0x7E6BA448 |
| second transmitter | ch3 (wait 0x7E6BA578) | 0x7E6BAF45(1) | read 0x7E6BA698 / write 0x7E6BA743, field read 0x7E6BA7E0, field write 0x7E6BA7F9 (150 callers), multi-read 0x7E6BA832 |
| third path | ch3 (wait 0x7E6BA59C) | 0x7E6BAF45(2) | 0x7E6BA8E2 / 0x7E6BA986 / field 0x7E6BAA1E |

- All three share semaphore 0x7E43EACA. The bus select calls 0x7E461469(224, n ≠ 0).
- The ch3 transmitter is also device 0x72 with the same register set, including the fixed init 0x7E6BB4AB. Its mode setters 0x7E6BBB37/0x7E6BBD13/0x7E6BC1F1/0x7E6BC6E5 hold `outevf_tmds_measurement` and `V_DROP_FLG`. **Inferred:** a second HDMI/TMDS transmitter that drives the accessory-port EVF (VF-4).
- The third path addresses device 0x98 (0x7E6BCC09: 0x12, 0x22–0x29, 0x34, 0x4D–0x59) and 0x88 (`evftx` debug 0x7E6B1F77). The device is unidentified.

### 3.5 Display-controller writers (0x9A900000; V offsets, I meanings)

| Function(s) | Registers (offset) | Role |
|---|---|---|
| 0x7E6B75C2 | 0x0C, 0x10, 0x14, 0x30, 0x34, 0x88, 0x260, then bank inits 0x7E6B8DBC (0x0F8–0x294), 0x7E6B91BA (0x054–0x1A0), 0x7E6B9333 (0x060–0x1B4), 0x7E6B9553 (0x004, 0x018–0x020, 0x228–0x240) | init (from VSC 0x7E6B5B39) |
| 0x7E6B749A → 0x7E6B77FF/7815/7872/789A, 0x7E6B78A5, 0x7E6B78E6 | 0x14 control bits; status 0x0C/0x14; frame update: shadow 0x0A4–0x0E0 → layer 0x038–0x04C, 32 words 0x300–0x37C | ISR / per-frame |
| 0x7E6B78BF | OR 0x20 or 0x60 into 0x04 (d0 ≠ 0) or 0x08 | update latch |
| 0x7E6B7BA0, 0x7E6B7BB9, 0x7E6B8B59 | 0x204, 0x208 | gamma (from `[display gamma]` 0x7E6B721B) |
| 0x7E6B8CB4; 0x7E6B8C8F | 13 words 0x1C8–0x1F8; 0x288–0x294 | colour matrix / colour adjust (from `COLOR MODE` 0x7E6B56E7) |
| 0x7E6B7CA7, 0x7E6B8441, 0x7E6B8D28; 0x7E6B8321 | read 0x194–0x19C; write 0x058/0x070 | geometry for VSC 0x7E6B63FA |
| 0x7E6B886E | 0x030, 0x1BC | TFT adjust / external-port TMDS (`ADJ CONT TFT`, `adj_ext_port_tmds_exe`) |
| 0x7E6B8D59/0x7E6B8D6C/0x7E6B8D7F/0x7E6B8D97 | 0x038/0x03C/0x040 and the second bank 0x9A901C38/3C | layer addresses (`[DisplayFrame]` 0x7E6B6F1A) |

The other single-register writers are in the TSV.

**Pattern:** a writer loads the absolute address `fc dc <addr32> mov imm32,a0` with 0x9A90xxxx, or `mov 0x9A900000,a0; add idx·4` (F022 style), and stores with `mov dN,(a0)`. None of these writers has strings; the role comes from the string-bearing caller.

## 4. DPS (PictBridge) engine in overlay A

### 4.1 Layout of overlay A (V call edges and rodata order)

| Range | Contents |
|---|---|
| 0x7F05C000–~0x7F05DBCC | BASIC |
| ~0x7F05DBCD–0x7F05E58F | RCU script server |
| 0x7F05E590–0x7F05E8D3 | **playback calendar helpers** (new, no strings): each is the only callee of an `api_calendar_*` wrapper 0x7E6762DC–0x7E67636E |
| 0x7F05E8D4–0x7F05E9CD | `md3d_hi_dbg` / `md3d_dmp_dbg` |
| **0x7F05E9CE–0x7F0645C0** | **DPS** |
| from 0x7F0645C1 | red-eye library |

### 4.2 DPS layers (V)

1. **Session / protocol, 0x7F05E9CE–0x7F060BFE.** The dispatcher 0x7F05E9CE(msg) splits on `msg & 0xF0000000`:
   - **App requests 0x1000000n** (table 0x7F06A0F8): 1 discovery 0x7F0603B7; 3 configurePrintService 0x7F06051B; 4 getCapability 0x7F060594; 5 getDeviceStatus 0x7F060637; 6 getJobStatus 0x7F0606A7; 7 startJob 0x7F060746; 8 abortJob 0x7F0607F2; 9 continueJob 0x7F06088D; 0xE end 0x7F060936.
   - **Transport events 0x2000000n** (printer file received 0x7F05EE65) and **abort 0x30000000**.
   - Printer requests are handled by 0x7F05F035 (table 0x7F069F50): notifyJobStatus, notifyDeviceStatus, getFileID. Other ops get the reply "not supported" (0x10020000).
   - Printer responses are handled by 0x7F05F156 (table 0x7F069F90). The DPS version is checked against {1.0, 1.1}.
2. **XML encoder, 0x7F060BFF–0x7F061CEC.** It writes the `<?xml?>` and `<dps xmlns=…>` envelope, then calls **builder table 0x7F06A130[op & 0xFEFF]**. The writer primitives are 0x7F061A36 (tag in forms 0–3), 0x7F061B3D (append), 0x7F061B88 (`%08X`/`%04X`/`%03d`).
3. **Argument checks, 0x7F061CED–0x7F062B88.**
   - Validator 0x7F062A9C: version byte ≤ 1, op 1..16, and the result range 0x1000–0x1003 for outputs (0x7F061F89).
   - It uses a **16-bucket open-addressed hash table 0x7F06A678** ({id, check} pairs, bucket = id & 15) with 12 ids. Examples: 2 → 0x7F062552, 0x102 → 0x7F06243B, 5 → 0x7F0626E1 (startJob, `../DCIM/` paths), 9/0x104 → 0x7F06289F (device status), 10/0x10A → 0x7F062A5E.
   - Range helper 0x7F061CED (13 callers).
4. **XML decoder, 0x7F062B89–0x7F0645C0.** It handles the envelope, `<input>`/`<output>`, `<result>` 0x7F062E4B, and the op-name lookup in 0x7F06A7DC. Then it calls **parser table 0x7F06AB58[op]**. The primitives are 0x7F0644D6 (match), 0x7F0643FF (skip whitespace and comments), 0x7F0641F3 (hex) and 0x7F064365 (attribute).

### 4.3 Operation index (op = name index in 0x7F06A7DC; V tables)

| op | name | builder | parser |
|---|---|---|---|
| 1 | configurePrintService | 0x7F060D17 | 0x7F062EAA |
| 2 | getCapability | 0x7F060F0F | **0x7F0634BE** `<capability>`, the 11 children of 0x7F06A920; `paperSize` attribute for paperTypes/layouts |
| 3 / 8 | getJobStatus / notifyJobStatus | 0x7F06103D / 0x7F061754 | 0x7F0637E5 (shared) |
| 4 / 9 | getDeviceStatus / notifyDeviceStatus | 0x7F061083 / 0x7F0617D4 | 0x7F063B47 (shared) |
| 5 | startJob | 0x7F0610C9 (jobConfig 0x7F06AA98, printInfo 0x7F06AB00, croppingArea `%04X`×4) | 0x7F063C9E |
| 6 / 7 | abortJob / continueJob | 0x7F061666 / 0x7F06170E | 0x7F063CED / 0x7F063D3C |
| 10 | getFileID | 0x7F061854 | 0x7F063D8B |
| 11–15 | getFileInfo, getFile, getPartialFile, getFileList, getThumb | **NULL** | **NULL** (→ −200): names only |
| 16 | result (no op element) | 0x7F061934 | 0x7F063F14 |

Bit 0x100 of the op marks an `<output>` (a response). Error codes: −100 null; −197 element missing; −198 bad value; −200 no builder/parser; −300 syntax/op/version; −400 no memory. B's 0x7F088D2C maps them to DPS result codes.

**Byte signatures:**
- **Builder:** `movm` entry; `fc a0 08 a7 06 7f` (`mov (0x7F06A708),a0`) or `…0c a7 06 7f`; `call 0x7F061A36`; no malloc.
- **Parser:** `movm` entry; calls 0x7F0644D6/0x7F0643FF/0x7F063F3D; a `call 0x7F0879CD` + `call 0x7F087BE5` pair (allocate and zero).
- **Check:** a plain `call` target of 0x7F062A9C that returns 0 or `mov -198,d0`.
- The full per-function index is in the TSV (`dps-*` rows).

### 4.4 Overlay A → B dependency, and the Usr2 claim (V)

- **The dependency.** There are 297 call edges from A to 36 targets in B, and **all of them come from DPS code** (BASIC, RCU, calendar and red-eye make none). Targets: the DPS pool malloc 0x7F0879CD / free 0x7F087B28; libc thunks 0x7F087BC7 strcpy, 0x7F087BD1 strlen, 0x7F087BDB strcmp, 0x7F087BE5 memset, 0x7F087BEF memcpy, 0x7F087BF9 memcmp (→ the 0x7E500Dxx runtime); the file transport 0x7F087D99–0x7F087F9D (`DREQUEST`/`DRSPONSE`/`HREQUEST`); the reply timer 0x7F088209; app notification 0x7F0886AD–0x7F0886E4; the trampolines 0x7F088D18 → encoder 0x7F060BFF and 0x7F088D22 → decoder 0x7F062B89; the error map 0x7F088D2C.
- **DPS_MAIN 0x7F087807 is in overlay B** (started by USTART4). It feeds A's dispatcher. So **PictBridge needs both overlays.**
- **Section 01 is right that A and B are separate Usr2 requests.** Usr2 0x7E505005 tests `btst 1` → overlay A (0xF000 B from 0x80EFB000 to 0xBF05C000, segment-4 constructors, USTART3), `btst 2` → overlay B (0x6B800 B from 0x80F1F000 to 0xBF080000, segment 5, USTART4) and `and 0x1000000` → ADJSLF; done flags in 0x602A9B48.
- **Why it matters.** The masks are independent, so **mask 2 alone loads B and starts DPS_MAIN without A** (V code). The callers seen pass 0xFFFFFF (A + B): firmware-update path 0x7E67EC80, self-adjust 0x7E675F05, vtable slot 0 0x7EBA139E. Masks 1, 2 and 0x1000000 alone come only from slots 1–3 of vtable 0x7EC90B30 (ctor 0x7EBA1370), not traced. **Calendar playback calls overlay A with no load check** (V), so A must already be resident (§7).

## 5. Platform gaps, 0x7E421020–0x7E520000

**Rule (V; script `$S/d3/proto/gaps/find.py`).** Of the 3,150 fwmap functions in the range, a function counts as *named* when sections 01, 13a, 13f or 14b give either:
- an address inside it, or
- an explicit range under 20 KB that holds its start.

Region-level ranges of 20 KB or more do not count (0x7E421020–0x7E426FFF, 0x7E45824B–0x7E46C308, padding). A *gap* is a run of unnamed functions spanning at least 1 KB. Result: **31 runs, 223 KB**; 1,325 functions named. Each run and its notable functions have `gap-run` / `function` rows in the TSV.

| Run | Role | Key entries / callers | V/I |
|---|---|---|---|
| 0x7E421C93–0x7E425F43 | **BML/STL flash library**: STL close 0x7E421D53, format 0x7E421DBA, open 0x7E421E79, **read 0x7E421EC8**, write 0x7E421F23; BML erase 0x7E421FB6, write 0x7E4220D1, read 0x7E42249E; block layer 0x7E423F09–0x7E42475D; thunks 0x7E4247BD–0x7E42482B; low-level part 0x7E424833–0x7E425F43 | lock pair 0x7E4215A2/0x7E4215B6; traced wrappers 0x7E451829–0x7E451D85; `fmem` 0x7E44F509 | V edges; split I |
| 0x7E4300D7–0x7E438BF1 (7 runs, 204 fns) | **uITRON 4.0 kernel internals**: acre/del, act/ter/dly/slp/wup, flag/sem/dtq/mbx/mtx, ref_*, loc/unl_cpu, dis/ena_dsp, sns_ctx 0x7E436577, kernel enter 0x7E432863 / exit 0x7E4328DA, scheduler 0x7E435FF4 (67 `kernel` TSV rows) | every task-context check returns E_CTX −25; per-CPU block (0x8FE00004)[(0x8050)] +28: in-ISR / CPU-locked / dispatch-disabled | V mechanics; names I (from caller shim names) |
| 0x7E44B6B0–0x7E44D6EE | ctor walker (14d) + **OSDB object dumpers** for S_SHELL (task, sem, flag, dtq, mutex, mbf header/row printers; error legend 0x7E44D439) | S_SHELL 0x7E44DBF5 | V |
| 0x7E45038D–0x7E450C4A | **SYSFMEM operation bodies** (BML read variants and retry, write/erase with read-back, STL thunks 0x7E450AA1–0x7E450AD3, boot-bank check 0x7E450C4B) | SYSFMEM 0x7E4520F3; `flash` shell | V |
| 0x7E45140B–0x7E4520F2 | second request poster 0x7E45140B, `prm fmem` 0x7E451515/0x7E4515F5, **traced BML/STL wrappers** 0x7E451873–0x7E451D85 (STL_READ = C3 F001) | fupsrv 0x7E54398B, ADJ | V |
| 0x7E452343–0x7E455F92 | **STL core** (sector map): entries 0x7E4546CA/0x7E4546D4/0x7E4546ED, write path 0x7E4551C1, recovery 0x7E455A6D | STL API only | V edges; role I |
| 0x7E455F93–0x7E45824A | prm settings store (getval 0x7E457C75, 2,168 callers) | section 07 §1 | V |
| **0x7E45B6BE–0x7E45CE11** | **ADC request scheduler**: `adc_request(a0)` **0x7E45BB10** (23 callers) switches on req byte 0 (1 → 0x7E45BB8C, 2 → 0x7E45BF47, 3 → 0x7E45BFBD, 7 → 0x7E45BCA8, 8 → 0x7E45BD81, 9 → 0x7E45BE60); completion 0x7E45CCA1; ISR bodies 0x7E45C820–0x7E45CA72; PER_IN init 0x7E45B6BE | UI keys 0x7E50B1B4–0x7E50B877, accelerometer, MEC 0x7E5175C9, PWR | V dispatch; what each type samples I |
| 0x7E45DCD3–0x7E45E205 | CCD-temperature task internals (13f's range ends at 0x7E45E205) | | V |
| 0x7E463124–0x7E463334 | **SIO I²C-mode helpers**: init/open/start/write/read | accelerometer, IOE, HDMI 0x7E6BA39B, touch, BT | V |
| 0x7E463376–0x7E4639F3 | 4-command dispatcher 0x7E463376 (cmd 0 calls strobe helpers 0x7E5E2152/0x7E5E2258) | camera core 0x7E626C76, EXP_MOVIE | V; role I (weak) |
| 0x7E465081–0x7E465582 | **soft-timer API**: `tmr_start` 0x7E4650A2 (124 callers), `tmr_stop` 0x7E4650DD (39), two lists by class | drivers, UI, lens, MEC | V; "1 ms / 2 ms" I |
| 0x7E465D10–0x7E466886 | **PER_PCONT client side** (ref-counted control on/off, PWM duty 0x7E466435/0x7E466448, `pcntdbg`) | cam, power | V edges; I |
| 0x7E46B24E–0x7E46B3D0; 0x7E46BA9F–0x7E46BBE5 | BT UART adapter; SIO-UART client thunks | `bt_get_data` 0x7E912F55; strobe TX 0x7E5DC0F7 | V |
| 0x7E46B3E3–0x7E46B74C | **hardware-timer client API** (open/start/stop/abort, free-run read 0x7E46B519, 38 callers) | VideoTimer, MEC, lens | V |
| 0x7E46BC44–0x7E46C0DA | **USF unit** (GIO 0x9A100124/12C; `usf` shell) | TAKE 0x7E5959B3, ADJ | V; "dust filter" I |
| 0x7E46C458–0x7E46CFFF, 0x7E473000–0x7E47EFFF | not code: segment-0 rodata | 14d | V |
| 0x7E5025C3–0x7E503A6D | **USR_FAST_APP step handlers** (fast start to shooting) | task 0x7E502140 | V strings |
| 0x7E505A93–0x7E505F2F | **CPUCONN remote kernel calls**: `needs_remote` 0x7E505A93, builders 0x7E505AD7–0x7E505C13, send-and-wait 0x7E505D91, server 0x7E505C44 → 0x7E505C8A | every Oly*Cpu wrapper | V |
| 0x7E50DD02–0x7E50F7F1 | **UI_SCREEN task** 0x7E50DD29 (OSD planes via `api_tft_*`) and the UI_OUT back half 0x7E50EF35–0x7E50F7B5 (beep → audio 0x7E95BD1D) | UI_OUT 0x7E50D858 | V edges; I |
| 0x7E510CA9–0x7E513399 | `mec` shell sub-commands, test/status decoders, mec_ev.c core (error logger 0x7E51320F) | `mec` 0x7E510A60 | V |
| 0x7E5138E5–0x7E514433 | MEC "L" low layer under LCOM 0x7E51339A | | V strings; role I |
| 0x7E514648–0x7E5167EB | **MEC core**: 128-B request pool `mec_alloc` 0x7E51470B (143 callers), update/free 0x7E51483B (119), per-phase handlers | | V |
| 0x7E516DD7–0x7E517790 | lock-by-name objects; ADC-sensed MEC inputs 0x7E5175C9/0x7E517671 | | V |
| 0x7E518C62–0x7E518E57 | MEC adjustment interface | ADJ overlay 0x7F0825E8 only | V |
| 0x7E518E91–0x7E51BA08 | **MEC sequence steps**, one pattern: take a block (0x7E51470B), store a completion callback (`mov imm32` of a function in this range), `calls (0x604F64xx)` | MEC core | V pattern |
| 0x7E51BA09–0x7E51BF66 | mec_timer.c: soft start 0x7E51BAC5 → 0x7E4650A2, stop 0x7E51BB59, HW 0x7E51BE0E | | V |
| 0x7E51BF67–0x7E520006 | lens tasks (section 02) | | V |

**SYSFMEM modes (correction to 01 §6; V).** The task 0x7E4520F3 dispatches on `mode & 0xFF00`, then on the full mode. The help text 0x7E475A79 prints the modes as 3 hex digits.

| Mode (hex) | `cmp` | Operation | Handler chain |
|---|---|---|---|
| 0x000, 0x002 | class 0 | BML_NormalWrite, BML_AdwordWrite | 0x7E44F197 → 0x7E4505D6 / 0x7E450754 / 0x7E450825 → 0x7E451B69 |
| 0x101, 0x103 | 257, 259 | BML_NormalRead | 0x7E44F11B → 0x7E45038D |
| 0x102 | 258 | BML_AdwordRead | 0x7E45045A / 0x7E450500 |
| 0x104–0x106 | 260–262 | not in the help text: status reads; 0x105 is a `ret` stub | 0x7E4503BF / 0x7E450401 / 0x7E450404 |
| 0x200 | 512 | BML_Erase | 0x7E44F3D0 → 0x7E4519C5 |
| 0x300 | 768 | STL_Write | 0x7E450A41 → 0x7E451CDB → 0x7E421F23 |
| **0x400** | **1024** | **STL_Read** | 0x7E4505A6 → 0x7E451D85 → 0x7E421EC8 |
| 0x500 | 1280 | STL_Delete | 0x7E450A71 → 0x7E451AE0 |
| 0x601–0x604 | 1537–1540 | STL_Init / Format / Open / Close | 0x7E450AA1 / 0x7E450AAC / 0x7E450AC0 / 0x7E450AD3 |

## 6. Corrections

1. **05 row "~0x7E91D279–~0x7E937CDD Blue SDK".** The stack also has part 1 at 0x7E915A1B–0x7E91962B (init, EVM, profiles, the **HCI layer**). That part sits inside 05's row "0x7E913984–0x7E91CFFF stack callbacks, iAP". Also, 0x7E91D279/0x7E91D289 are iAP getters; L2CAP starts at 0x7E91D29F (V).
2. **Link "table" 0x7DAC4C68:** it holds **one** 320-byte record (the loops stop at `cmp 1`), so there is one ACL link (V).
3. **C3 F028: "0x7E926E88 picks the mode".** 0x7E926E88 is the start function of ME op type 22 (Park): op table 0x7EBB3B18 slot 21 (V).
4. **08 §1.1: "DPS XML library 0x7F061020–0x7F068F9C".** The DPS range is 0x7F05E9CE–0x7F0645C0, and the red-eye library follows (V). 0x7F05E590–0x7F05E8D3 is playback-calendar code (new).
5. **C3 F075: "0x7F062A5E … record type 10 (string)".** The 10 is op id 10 (getFileID) (V). The builder table base is 0x7F06A130 with 17 slots, not "0x7F06A134, 10 entries"; slots 11–15 are NULL (V).
6. **01 §6:** the SYSFMEM modes are hex (table above).
7. **01, Usr2:** the claim that A and B load separately is correct. Add two facts (V):
   - the request masks are independent;
   - DPS_MAIN runs in overlay B, so PictBridge needs both overlays.
8. **13f:**
   - The CCD-temperature range ends at 0x7E45E205.
   - Add rows for the SIO I²C helpers 0x7E463124–0x7E463334, the hardware-timer API 0x7E46B3E3–0x7E46B74C and the USF unit 0x7E46BC44.
   - "HDMI on SIO ch2 and ch3": ch2 carries the HDMI-port transmitter and CEC. ch3 carries a second device-0x72 transmitter (I: EVF TMDS) and a device 0x98.
9. **08 §2, the "Analog Devices part":** the evidence is now register-level. It uses main map 0x72, a CEC map at 0x78 read from register 0xE1, and the ADV7511-family register set (I: family; V: numbers).

## 7. Open questions

1. Name the HCI-layer functions in 0x7E917AFE–0x7E91962B. In particular: where does it handle Number_Of_Completed_Packets (0x13 never reaches the ME table), and how does it route ACL data to L2CAP?
2. The RFCOMM/SDP split near 0x7E933AEE–0x7E933C47 comes from RAM pages and endianness (I). Confirm it with the SDP PDU parser (PDU ids 2/4/6).
3. The ME op types 12 (0x7E92A3CB) and 45 (0x7E92A99C) are not resolved to commands.
4. The CEC opcode handling (which messages beyond the remote keys and standby) has not been decoded.
5. Identify the device 0x98/0x88 on the third ch3 path. Is the ch3 transmitter the VF-4 link?
6. The meanings of the display-controller registers; the 0x9A901C00 bank.
7. Does any caller use Usr2 vtable slot 2 (B) without slot 1 (A)? What loads A before the calendar view?
8. Platform gaps:
   - the role of 0x7E463376;
   - three `acre_*` object types (0x7E430201, 0x7E4302C2, 0x7E4303A9);
   - the MEC "L" layer 0x7E5138E5.
