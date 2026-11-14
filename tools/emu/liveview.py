"""A live-view rig for scenario runs: the E-PM2 mov layer and art tasks, started the way the firmware starts them.

    from liveview import LiveView
    lv = LiveView("/tmp/scratch/pinned.block0.bin")
    lv.settings[38017] = 119            # Picture Mode: Key Line
    lv.start()                           # constructors, module inits, tasks to their first wait, "Through Start"
    r = lv.frame()                       # one frame event; every task runs until it waits. r is a Frame
    r.picture, r.alloc_error, r.art_code, r.pcs, r.writes, r.faults ...

What runs as real firmware code (verified by the executed pcs of each run):
  - the static constructors of segments 1, 2 and 3 (0x7E44B6B0), which create the image buffer regions;
  - the module init functions that the start-up list 0x7E503DD4 calls for the IMG library, the buffer manager,
    the art module and the mov layer (INIT_SITES);
  - the task bodies named in TASKS (MOV_TASK 0x7E6C33B5 and the others), from their real entries, each on its own
    stack, with the task switches done by tools/emu/osmodel.py (no pre-emption).
What does not:
  - devices. Writes to device registers are dropped and logged; reads give 0 (Scenario.mmio_values to change);
  - "the image processor finished a job": the flag that the IMG library waits for is set at once (os.auto);
  - the uITRON kernel (osmodel.py); the settings store (Scenario.settings; unset ids read 0 and are listed);
  - the white-balance module 0x7E579C34-0x7E581FB0 and the CPU cache control 0x7E45DA29-0x7E45DAED (stubbed
    whole), and the soft-float multiply 0x7E5018E8 (done in Python: om-emu's float unit faults on its inputs);
  - pixel data: buffers hold zeros.
"""
import os, struct
import osmodel, scenario
from scenario import Scenario, BASE

TASKS = ["MOV_TASK", "MOV_SUB_TASK", "ART_IMG_CM", "ART_IMG_CS", "MOVDISP_TASK", "MOVCOLOR_SUB",
         "MOVART_TASK", "ART", "ART_IMG_CF", "MOVCOLOR"]
INIT_SITES = [0x7E5046D4, 0x7E5046DB, 0x7E50474D, 0x7E5047DB, 0x7E504837, 0x7E504859, 0x7E50487B, 0x7E50489D,
              0x7E5048BF, 0x7E5048EE, 0x7E50491D, 0x7E504974]
"""Call sites in the start-up function 0x7E503DD4: IMG library 0x7E544AA9, buffer manager 0x7E578310, art module
0x7E71BEC7, 0x7E548756, mov art 0x7E6CBE53, 0x7E6F43DF, 0x7E6D11E8, 0x7E6D08DC, mov 0x7E6C310E, 0x7E6F821A,
0x7E6F459D, 0x7E70B3F8."""
CTOR_RUNNER, CTOR_SITE = 0x7E44B6B0, 0x7E503DF0
IMG_WAIT_SITE = 0x7E55EB51          # return address of the flag wait in the IMG library's "job done" wait 0x7E55EB40

MARKS = [(0x7E6C6853, "mov_image_process"), (0x7E6C610B, "expose setter"), (0x7E6C6498, "art change notifier"),
         (0x7E6CD1F2, "mov_art_exec_init"), (0x7E714833, "heap mode chooser"), (0x7E578C60, "heap set mode"),
         (0x7E5789ED, "heap re-partition"), (0x7E6CADD8, "heap mode check"), (0x7E6C6532, "art picture alloc"),
         (0x7E6D4B22, "2 x 614400 alloc"), (0x7E6CD4B7, "line buffer alloc"), (0x7E6CADFE, "free all art buffers"),
         (0x7E6C6A11, "\"art_buff alloc error\""), (0x7E6C8841, "frame builder"), (0x7E6C74BE, "job setup"),
         (0x7E6C7BB0, "set_out_area_param"), (0x7E6CD9C5, "set_line_yc_param"), (0x7E6CD892, "set_color_yc_param"),
         (0x7E6CCBE1, "set_artpacket"), (0x7E6DABAF, "img exec"), (0x7E6CA62B, "display update"),
         (0x7E725A1B, "Key Line pass 1"), (0x7E7262F1, "Key Line pass 7"), (0x7E7264A9, "Key Line pass 8"),
         (0x7E7266D9, "Key Line pass 9 (overlay)"), (0x7E7267D9, "Key Line pass 10"), (0x7E707880, "combine job")]
"""Places on the live-view art path (NOTES.md sections 11 and 12). Frame.path() lists the ones a step reached."""

# mov layer RAM (NOTES.md of experiments/2026-11-14-focus-peaking)
LV_STRUCT, MOV_STATE, MOV_PENDING = 0x605B1CD0, 0x605B03D0, 0x605B03D4
EXPOSE, LAST_EXPOSE, MODE_BYTE, ART_RECORD = 0xA07507CC, 0xA07507C9, 0x605B091C, 0x605B038C
ALLOC_ERR, FRAME_OK = 0x605B0609, 0x605B060C
LINE_BUFS = 0x605B0AF0              # 6 words; +4 job copy, +8 IMG_PARAM copy, +16 / +20 the line image buffers
HEAP_MODE, HEAP_MODE2, HEAP_FLAGS = 0x605157CC, 0x605157CE, 0x605157D0
MOV_TMO = 0x605B0418
HEAP_ALLOC_RET = 0x7E578EB9         # the ret of the image-work heap alloc 0x7E578D43: d0 = block, (32,sp) = size
HEAP_FREE, HEAP_SET_MODE, HEAP_REPARTITION = 0x7E578EBC, 0x7E578C60, 0x7E5789ED
ERROR_REPORT, MOV_ERROR_PRINT = 0x7E426D4B, 0x7E6D144F
CMD_THROUGH_START, CMD_THROUGH_END = 1, 2


def task_table():
    """{name: (entry, priority, stack size, cpu)} from build/map/tasks.tsv."""
    out = {}
    with open(os.path.join(scenario.MAP_DIR, "tasks.tsv")) as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split("\t")
            out[p[2].split(" ")[0]] = (int(p[3], 16), int(p[4]), int(p[5], 16), int(p[0]))
    return out


class Frame:
    """What one step did: the results of every task run in it, and the mov state after it."""

    def __init__(self, label):
        self.label, self.results, self.state, self.events, self.stale = label, [], {}, [], []

    def _all(self, attr):
        out = []
        for r in self.results:
            out += getattr(r, attr)
        return out

    @property
    def pcs(self):
        s = set()
        for r in self.results:
            s |= r.pcs
        return s

    @property
    def writes(self):
        return self._all("writes")

    @property
    def mmio(self):
        return self._all("mmio")

    @property
    def stubs(self):
        return self._all("stubs")

    @property
    def faults(self):
        return ["%s: %s\n      %s" % (r.label, r.fault, "\n      ".join(r.backtrace)) for r in self.results if r.fault]

    @property
    def insns(self):
        return sum(r.insns for r in self.results)

    def calls(self, addr):
        """True if the function at addr was entered in this step (natively or as a stub)."""
        return addr in self.pcs or any(s[0] == addr for s in self.stubs)

    def path(self):
        p = self.pcs
        return [n for a, n in MARKS if a in p]

    def summary(self):
        s = self.state
        return ("%s: %d task runs, %d insns, %d device writes; state %d, expose %d, art record 0x%X, heap mode %d, "
                "picture %s, alloc error %s%s" % (self.label, len(self.results), self.insns,
                                                  sum(1 for m in self.mmio if m[0].startswith("w")), s["mov_state"],
                                                  s["expose"], s["art_record"], s["heap_mode"], s["picture"],
                                                  s["alloc_error"], "; FAULT" if self.faults else ""))


class LiveView:
    def __init__(self, image, name=None, tasks=TASKS, log_writes=(), insn_limit=3_000_000):
        self.sc = Scenario(image, name=name, insn_limit=insn_limit)
        sc = self.sc
        self.os = osmodel.install(sc)
        self.settings = _Settings(sc)
        self.log_writes = list(log_writes)
        self.trace = True
        self.calltrace = False
        self.stubbed = {"white-balance module": sc.stub_module(0x7E579C34, 0x7E581FB0, "WB module"),
                        "CPU cache control": sc.stub_module(0x7E45DA29, 0x7E45DAED, "CPU cache control")}
        sc.stub(0x7E5018E8, _fmul, "float multiply 0x7E5018E8 (in Python)")
        self.os.auto_sites[IMG_WAIT_SITE] = 3
        u16 = lambda a: struct.unpack_from("<h", sc.image, a - BASE)[0]
        self.FLG, self.QCMD, self.QREP = u16(0x7E43EBA6), u16(0x7E43ED2A), u16(0x7E43ED34)
        tt = task_table()
        self.tasks = {}
        for n in sorted(tasks, key=lambda n: tt[n][1]):           # priority order (lower number first)
            entry, pri, stack, cpu = tt[n]
            self.tasks[n] = sc.task(n, entry, frame=(0, 0), stack_size=stack)
        self.frames = []
        self.setup_results = []
        self.events = []                    # (kind, detail) since the last step: heap calls, firmware error reports
        self.blocks, self.freed = {}, {}    # image-work heap: live blocks {address: size}, freed and not reused
        self.stale = []
        sc.on_device_write = self._on_device_write
        sc.probe(HEAP_ALLOC_RET, self._on_alloc, "heap alloc return")
        sc.probe(HEAP_FREE, self._on_free, "heap free")
        sc.probe(HEAP_SET_MODE, lambda sc, g: self.events.append(("heap set mode", "%d (was %d), %d live blocks" % (
            g["d0"] & 0xFFFF, sc.r16(HEAP_MODE), len(self.blocks)))), "heap set mode")
        sc.probe(HEAP_REPARTITION, lambda sc, g: self.events.append(("heap re-partition", "%d live blocks: %s" % (
            len(self.blocks), ", ".join("0x%08X+%d" % kv for kv in sorted(self.blocks.items()))))), "heap re-partition")
        sc.probe(ERROR_REPORT, lambda sc, g: self.events.append(("error report", "code 0x%08X from %s" % (
            g["d0"], scenario.funcs().name(g["mdr"])))), "error report 0x7E426D4B")
        sc.probe(MOV_ERROR_PRINT, lambda sc, g: self.events.append(("mov error print", "%r value %d" % (
            sc.emu.cstr(g["a0"], 60), g["d1"]))), "mov error print 0x7E6D144F")

    def _on_alloc(self, sc, g):
        ptr, size = g["d0"], sc.r32(g["sp"] + 32)
        self.events.append(("heap alloc", "%d bytes -> 0x%08X (heap mode %d)" % (size, ptr, sc.r16(HEAP_MODE))))
        if ptr:
            self.blocks[ptr] = size
            for a in [a for a, n in self.freed.items() if a < ptr + size and ptr < a + n]:
                del self.freed[a]

    def _on_free(self, sc, g):
        ptr = g["d0"]
        known = ptr in self.blocks
        self.events.append(("heap free", "0x%08X%s (heap mode %d, mode at the last alloc %d)" % (
            ptr, "" if known else " NOT A LIVE BLOCK", sc.r16(HEAP_MODE), sc.r16(HEAP_MODE2))))
        if known:
            self.freed[ptr] = self.blocks.pop(ptr)

    def _on_device_write(self, sc, addr, value, size, pc):
        """A device register gets an address inside a block that was freed and not given out again: the image
        processor would be told to use memory that the heap no longer reserves. Checked at the time of the write."""
        if size == 4 and self.freed:
            v = value & 0x1FFFFFFF
            for a, n in self.freed.items():
                if (a & 0x1FFFFFFF) <= v < (a & 0x1FFFFFFF) + n:
                    self.stale.append((addr, value, pc, a, n))

    def close(self):
        self.sc.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # --- start
    def start(self, through=True):
        sc = self.sc
        for seg in (1, 2, 3):
            self._setup(sc.call(CTOR_RUNNER, {"d0": seg}, frame=sc.frame_at(CTOR_SITE), label="static constructors, segment %d" % seg,
                                trace=False, mmio_trace=False))
        for site in INIT_SITES:
            self._setup(sc.call_site(site, label="init called at 0x%08X" % site, trace=False, mmio_trace=False))
        f = self.step("tasks to their first wait")
        if through and not f.faults:
            f = self.command(CMD_THROUGH_START, label="Through Start")
        return f

    def _setup(self, r):
        self.setup_results.append(r)
        if r.fault:
            raise scenario.EmuError("setup: %s\n  %s" % (r.summary(), "\n  ".join(r.backtrace)))

    # --- steps
    def step(self, label):
        """Run every ready task until all wait. Returns a Frame."""
        f = Frame(label)
        f.results = self.os.schedule(list(self.tasks.values()), trace=self.trace, log_writes=self.log_writes,
                                     calltrace=self.calltrace)
        f.events, self.events = self.events, []
        f.stale, self.stale = self.stale, []
        s, sc = f.state, self.sc
        s["mov_state"], s["pending"] = sc.r32(MOV_STATE), sc.r32(MOV_PENDING)
        s["expose"], s["last_expose"], s["mode_byte"] = sc.r8(EXPOSE), sc.r8(LAST_EXPOSE), sc.r8(MODE_BYTE)
        s["art_record"] = sc.r16(ART_RECORD)
        s["alloc_error"] = bool(sc.r8(ALLOC_ERR))
        s["heap_mode"], s["heap_flags"] = sc.r16(HEAP_MODE), sc.r16(HEAP_FLAGS)
        s["line_bufs"] = struct.unpack("<6I", sc.read(LINE_BUFS, 24))
        s["lv_struct"] = sc.read(LV_STRUCT, 0x30)
        s["picture"] = None
        self.frames.append(f)
        return f

    def command(self, cmd, ptr=0, label=None):
        """Send a mov command (1 Through Start, 2 Through End, ...) as the command queue would deliver it."""
        self.os.post(self.QCMD, struct.pack("<4I", self.QREP & 0xFFFFFFFF, 0, cmd, ptr))
        self.os.flags[self.FLG] = self.os.flags.get(self.FLG, 0) | 2
        return self.step(label or "command %d" % cmd)

    def frame(self, label=None, timers=True):
        """One frame event for the mov task (flag bit 1), then every task until all wait.
        timers: first let the running software timers expire (the mov frame-time timer paces art frames)."""
        pre = self.os.fire_timers(trace=self.trace, log_writes=self.log_writes) if timers else []
        self.os.flags[self.FLG] = self.os.flags.get(self.FLG, 0) | 1
        f = self.step(label or "frame %d" % (sum(1 for x in self.frames if x.label.startswith("frame")) + 1))
        f.results = pre + f.results
        f.state["picture"] = f.calls(0x7E6CA62B)
        return f


class _Settings:
    """lv.settings[id] = value (any index) or lv.settings[(id, index)] = value."""

    def __init__(self, sc):
        self.sc = sc

    def __setitem__(self, k, v):
        self.sc.settings[k if isinstance(k, tuple) else (k, None)] = v

    def __getitem__(self, k):
        return self.sc.settings[k if isinstance(k, tuple) else (k, None)]

    def update(self, d):
        for k, v in d.items():
            self[k] = v


def _fmul(sc, g):
    x = struct.unpack("<f", struct.pack("<I", g["d0"]))[0]
    y = struct.unpack("<f", struct.pack("<I", g["d1"]))[0]
    try:
        r = struct.unpack("<I", struct.pack("<f", x * y))[0]
    except OverflowError:
        r = 0x7F800000 | ((g["d0"] ^ g["d1"]) & 0x80000000)
    return {"d0": r}
