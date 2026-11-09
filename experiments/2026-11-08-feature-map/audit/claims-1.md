# Audit batch 1: claims to check

## 01-11  (from sections/01-platform.md, line 11)

- There are two debug shells. S_SHELL is a system monitor (prompt `:-) `) on a memory-mapped serial port. U_SHELL (prompt `USR> `) has 54 command families in a {name, handler} table. A `:` line in S_SHELL sends the input on to U_SHELL. The same U_SHELL dispatcher is also reachable over USB through the factory-adjustment PTP operation 0x902B. **[V]**

## 01-31  (from sections/01-platform.md, line 31)

- `ID→var` table at 0x7E43E948 (u16 per object name). The boot code reads task IDs from here: entries 0–24 are 0x8085…0x80E0, and entry 25+ holds 1, 2, 3…. **[V]**

## 01-47  (from sections/01-platform.md, line 47)

| 0x1001 | 7E42691F | 1 | dyn | **CPU1 boot task** (attr TA_ACT) **[V]** |

## 01-104  (from sections/01-platform.md, line 104)

- The log goes through `0x7E503A6E`. The `usr fast` command (0x7E502111/0x7E5023E1) prints it ("UsrFastAppDebug!"). **[V]**

## 01-186  (from sections/01-platform.md, line 186)

- Upload: `rcu_serv_upload` → `bas_rcu_load` 0x7F05DF43. That function mounts the media and reads up to 16 KiB from `RCUOLYMP` / `R0240001.RCU` (8.3 names) into 0xBC620000. Then `0x7F05DDF0` rewrites the symbols, and `flash_mem` 0x7F05E041 calls `0x7E675700(mode 4, …)`, the resource/flash writer. **[V]** For the call chain, **[I]** that mode 4 is a script area.

## 01-196  (from sections/01-platform.md, line 196)

| PER_CCD_TEMP_MAIN (0x2D, 7E45DBB5) | Every 10 s (`dly 10000`) runs a state/event table (0x7E4C4FF8). Result 1 triggers a measurement (`0x7E45DC2C(3)`). Thresholds: lock / warn / attn1. **[V]** for the loop, **[I]** for the threshold meaning. |

## 02-30  (from sections/02-lens-power-firmup-take.md, line 30)

- The user start task 0x7E503DD4 (strings `Usr0`, `[usr]firmup`, `USTART1`) calls 0x7E5436D1 at 0x7E5045F4 and keeps the result in d2. At 0x7E504A59: if d2 == 1 it prints `[usr]firmup` and starts task FIRMUP_CLI (id at 0x7E43E9A0). Otherwise it calls 0x7E54374C, 0x7E5437AC and starts USTART1 (normal boot). **verified**

## 02-33  (from sections/02-lens-power-firmup-take.md, line 33)

- Which physical power-on cause (key combination) those factor values mean is **not decoded**. 0x602A9B54 is cleared by 0x7E505694 when 0x7E509CA3(4) == 0 and byte 0x604154E9 != 9. **verified (code); meaning inferred: a key held at power-on.**

## 02-110  (from sections/02-lens-power-firmup-take.md, line 110)

- **0x7E5448FB** (per section, modes 0 and 2): if header byte 21 == 1 → `[firmup]DeSecramble` → 0x7E54343F. Then checksum 0x7E54337D with type 1. **verified**

## 02-154  (from sections/02-lens-power-firmup-take.md, line 154)

- **LENS_FIRM_UP** 0x7E52FD56: reads queue 0x7E43ED20, runs 0x7E52FDC3 → 0x7E52FE8C, replies. 0x7E52FE8C stores the header pointer at 0x604F9390 and packet count `(size>>7) + (size & 127)` at 0x604F9394 (128-byte packets; the formula is literal). It picks lens protocol type 1 or 2 (0x604F943E, from 0x7E51FDB4) and runs step callbacks 0x7E52FFB3 / 0x7E530020 / 0x7E53008E / 0x7E530103 sending lens commands 0/3/4/5 (or 0x1000/0x1003/0x1004/0x1005 for type 2). Each step retries up to 3 times, then fails with 0x6608/0x6601/0x6604/0x6605. **verified** structure; command meanings **inferred**. Globals named by 0x7E53053F: `g_lens_firmup_send_num/ng/compare`, `g_firmup_id/hw_version/version/extension/serial_num[12]/recv_data[128]/err_status/connected_info/total_send`. A `compare` and `version` field exist, so the lens side may check versions (**inferred**, not traced).

## 02-162  (from sections/02-lens-power-firmup-take.md, line 162)

- **Tasks** (all **verified** as queue servers: read Oimf queue → handler → reply): LENS_MAIN 0x7E51BF67 (queue 0x7E43ED1E, handler 0x7E51BFBA), LENS_ASKDATA 0x7E51F77D (0x7E43ED1C → 0x7E51F7C5), LENS_FLASH 0x7E53086F (0x7E43ED22; cmd 1 → 0x7E5308E0, 2 → 0x7E530DEF, 3 → 0x7E531540), LENS_FOCUS_LIMIT 0x7E532218 (0x7E43ED24 → 0x7E532240; also called from TakeFcs `limit:` 0x7E592D75), ZOOM 0x7E538D9B (waits event bit 2, then queue 0x7E43EDDE → 0x7E538E60 if 0x7E5224F4() else 0x7E538D76).

## 02-171  (from sections/02-lens-power-firmup-take.md, line 171)

- **BCHK_MAIN** 0x7E53A1D0: reads queue 0x7E43ECD0 with a **1000 ms timeout**; on timeout, if polling is enabled (0x7E53A37F) → 0x7E53A472 (periodic check). Commands: 3/4/5 → 0x7E53A2E9 (check with a mode byte), 6/7 → enable/disable polling (0x7E53A376(1/0)), 8 → 0x7E53A485. **verified**. Debug shell 0x7E539672 (`vbat`, `vac`, `tmp`, `pbhtmp`, `src` 1=AC 2=BAT, `level`, events `inter_start_rec`, `before-rec`, `before-fat`, …). Event names `EBCHKBATT`, `EBCHKAD`, `EBCHKTIMER` at 0x7E53A049. **inferred**.

