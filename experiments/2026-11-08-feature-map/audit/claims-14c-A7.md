# Audit A7 (14c resample)

## 14c-12 (sections/14c-app-protocols.md, line 12)

| 0x7E966000–0x7E9698EB | HIGHLEVEL_MAIN, HLS OS wrapper (callers of kernel 0x7E44xxxx, e.g. 0x7E96985A), logger, growable array | V |

## 14c-14 (sections/14c-app-protocols.md, line 14)

| ~0x7E9EA381–0x7EB7FC90 | Cap*, CmpSts*, CmpSqp*, Cmp* (one file per class; true file starts in §1.1) | V |

## 14c-15 (sections/14c-app-protocols.md, line 15)

| 0x7EB7FC91–**0x7EB84344** | `CmpSts_SingleStillShootingSequence_NEW` chart; its last function 0x7EB83ECB ends with `ret` at 0x7EB84342 (not ~0x7EB854FF) | V |

## 14c-16 (sections/14c-app-protocols.md, line 16)

| **0x7EB84345–0x7EB85562** | **Com_EvSenderManager (static module, no `this`)**: sender 0x7EB84345 (4,143 B; maps APP_EVENT codes to 41 event classes 16070…27522; only caller HLS_EVENT 0x7E96DD58), "set wait code" 0x7EB85398/0x7EB8543C (callers CapThr 0x7EA1D60D/0x7EA1D68E), `Com_EvSenderManager buffer overflow!` 0x7EB854E0. All use globals 0x602B48A8–0x602B48E0 | V |

## 14c-18 (sections/14c-app-protocols.md, line 18)

| 0x7EB8C265–**0x7EB93385** | `Dev*` device classes part 1; the last Dev string user is `DevSor::stop()` 0x7EB93362, then 7 six-byte setters 0x7EB93386–0x7EB933AA and small DevSor helpers to 0x7EB93422 | V |

## 14c-97 (sections/14c-app-protocols.md, line 97)

- **Threads (V, thread-name strings; answers 13c open question 3):** `HLS_CALLBACK` 0x7E96CA56, `HLS_EVENT` 0x7E96DB78 (singleton 0x602B0EE4), `HLS_USER` 0x7E9E762F (OlyHfwUserSettingManager). All three are OMThread (0x7EBA708D) active objects.

## 14c-99 (sections/14c-app-protocols.md, line 99)

- **EVFW router (V):** singleton 0x602B1FE8 (getInstance 0x7E974D11, 482 callers; ctor 0x7E999809, two collections at +4/+20), delivery method 0x7E999883. It handles **11775** register forward, **11776/11777** subscribe (code / range: find or create a 44-byte topic 0x7E9E5384 and add the observer), **11779/11780** unsubscribe (remove the observer; drop the topic when empty), **2201** run an API callback on HLS_CALLBACK, **2205/2206** add/remove a listener (+20), **11794/11795/11800/11801/11802/11803** subscribe/unsubscribe at HLS_USER (all settings, or setting group 0..21), **11805** a record in the HLS_EVENT trace ring. Errors return 0xF0000016.

## 14c-100 (sections/14c-app-protocols.md, line 100)

- **Correction to review F036:** event 11779 is **unsubscribe**, not publish. CapGSld 0x7EA56A6B unsubscribes its observers +1180/+1156/+1204 from topics **0x04170003/0x04170002/0x04170001**; `gpu_slide_play` 0x7EA56935 subscribes (11776, ctor 0x7E96B3E4) to 0x04170003 with +1180 (V).

## 14c-110 (sections/14c-app-protocols.md, line 110)

| 4 | `TAKERDY_NORMAL_send` 0x7EA94AF9 → CapTak slot **75** (+300) 0x7EA33ECA: `api_rec_Take_Ready_Ext(kind 0x5000 if sequence flag 0x10000004 is set, else 0x0FFF; sub 1..5)`, stops a running movie effect first, and hands the returned request handle (+692) to 0x7E9E8A3A (role not traced); `TAKERDY_FAST_send` 0x7EA94C22 → slot **73** (+292) = kind 0x3000 "Fast"; `TAKERDY_ABORTPROC_send` 0x7EA94BE8 → slot **72** (+288) 0x7EA33DC7 = kind 0 "End"; if the API returns a handle it sends 11805 to the EVFW router (argument 1) or 11775 to the object at +1324 (otherwise). ABORTPROC first runs TAKERDY_NORMAL when its second argument is 1 | V |

## 14c-133 (sections/14c-app-protocols.md, line 133)

- **CapBuf_BufferManager** 0x7E9EB318–0x7E9EE543: `initializeBuffer` 0x7E9EB41D (gets CapTak), handle alloc 0x7E9EC76D (in-use list append F030), `BM_F_*`/`BM_NULL_*` per-kind allocators 0x7E9EB7BC–0x7E9EC5C0, `HandleList_Start` dump 0x7E9EBF14, `TraceDump_Start` 0x7E9ED35E, conversions `ATH/ATHM/THA/THF` 0x7E9EDB66–0x7E9EDC5F. 0x7E9EBA3D is the trace logger: it prints `BM_Alloc/Alloc_Multi/Free/Free_Pic/Num(%02d)` only when kind bit 1/2/4/8/16 is set in 0x602B287C (the `sdk dbgbm` mask, I) (V).

## 14c-136 (sections/14c-app-protocols.md, line 136)

- **CapThr_ThroughImageFacade** 0x7EA37F85–0x7EA39105: getInstance (26 callers, 980-B singleton), ctor 0x7EA37FC0 (builds CapThr_ThroughImage at +300), initRelations 0x7EA3819B (F034), live-view take control 0x7EA383CF (`api_rec_Continuous_Expose`, `Control_Focus`, `End_Take_Control`), `isActive()` 0x7EA385C1, `Trigger Force stop` 0x7EA388B8 (V).

## 14c-144 (sections/14c-app-protocols.md, line 144)

- **Mechanism (V):** 22 GUI static initialisers in the C++ ctor table **0x7F033AC8–0x7F033B7B** (45 entries; walker 0x7E44B6B0 id 3 loads 0x7F033AC8 with size 180; the word at 0x7F033AC4 is slot 0 of the vtable 0x7F033AC4 stored by 0x7EECC6C7 (A6 2026-11-09)) fill RAM tables of 8-byte pointer-to-member records `{−1, method}` (21 of them; 0x7ED9855F writes one null record `{0, 0}` at 0x602BC058 and has no dispatcher (A6 2026-11-09)); for 21 of them exactly one other function loads the table base (the dispatcher). Example: 0x7ED98B95 fills **77** records at **0x602BC070–0x602BC2D7**; the dispatcher 0x7ED99847 (vtable word 0x7EFD101C) first reads data-model values into its fields (0x7ECEF64F(record, size) calls) (A6 2026-11-09), then calls all 77 in order (`cmp 77,d2` loop), then writes data-model values (0x7ECEF667). Other tables (init → base, n, dispatcher): 0x7ED86DA6 → 0x602BB094 (22, 0x7ED87077, `IGui_Controler`); 0x7ED8ECE2 → 0x602BB7CC (18); 0x7ED8F435 → 0x602BB8DC (59); 0x7ED912E5 → 0x602BBAB4 (42); 0x7ED9319E → 0x602BBCA0 (60); 0x7ED94F0D → 0x602BBE80 (43); 0x7ED9D151 → 0x602BC2D8 (46, 0x7ED9D844); 0x7EDC2829 → 0x602BC5A4 (3, `Warning_Viewer::Update`); 13 smaller ones (1–7 records). fwmap shows 0 callers for all these methods because the only reference is the `mov imm32` inside the initialiser.

