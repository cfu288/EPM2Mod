"""A small Python model of the uITRON services that E-PM2 code reaches through the `Oly*` kernel wrappers.

The emulator has no kernel state (no tasks, no flags, no queues exist), so the real services would only return
errors. install(sc) puts stubs on the wrapper entries and keeps the objects in Python:

  event flags   OlyEvSt 0x7E449030 / 0x7E449083 (set), OlyEvWt 0x7E4490AF (wait), OlyEvCl 0x7E449175 (clear),
                kernel "reference" call 0x7E434E26 (read the pattern)
  queues        OlyQeRd 0x7E449218, OlyQeWr 0x7E4492B9, kernel count call 0x7E434EF2 (messages are byte strings)
  data queues   kernel calls 0x7E436343 / 0x7E433EFE / 0x7E431BBC (send one word), 0x7E434B00 / 0x7E437192 (receive)
  semaphores    OlySmWt 0x7E449409, OlySmSi 0x7E4494A1 / 0x7E4494E9 (a semaphore starts with count 1)
  timers        driver calls 0x7E4650A2 (start: mode, ms, callback, argument) and 0x7E4650DD (stop). A started
                timer is kept in os.timers; os.fire_timers() calls the callbacks (the scenario decides when time passes)
  tasks         OlyTaSS 0x7E449605 (sleep: returns at once, the time is added to os.slept_ms),
                OlyTaSt / OlyTaSp / OlyTaWu (logged, return 0)

A wait that cannot be met: with a timeout of 0 the service returns its "timeout" value; in a task (sc.task) the
task blocks (scenario.BLOCK) until the scenario makes the object ready; in a plain sc.call the model looks in
os.auto_sites: {return address of the wait call: bits} (a flag wait from that call site is met at once), and in
os.auto: {("flag", id): bits} / {("sem", id): True} / {("dtq", id): word} / {("queue", id): bytes}. An entry
there stands for "an interrupt or another task supplies this at once" and every use is logged in os.log. With
no entry the call ends with a fault text that names the object, so nothing waits silently.

The names and argument orders were read from the wrappers' code (register use and their debug strings). The
wait modes are simple: a flag wait is met when any waited bit is set; it returns the whole pattern
and clears the whole pattern (the kernel does that for a flag made with the clear attribute, 0x7E437870; the
attribute of each flag was not read from the kernel tables: list the exceptions in os.keep_flags). This is a model, not the kernel: priorities, time-outs that
expire, and pre-emption do not exist here.
"""
from collections import deque
from scenario import BLOCK

TIMEOUT = -2 & 0xFFFFFFFF          # what the wrappers return for the kernel's E_TMOUT (-50)


class Stuck(Exception):
    pass


class OSModel:
    def __init__(self, sc):
        self.sc = sc
        self.flags, self.queues, self.dtqs, self.sems = {}, {}, {}, {}
        self.auto = {}
        self.auto_sites = {}                            # {return address of an OlyEvWt call: bits}: as auto, by call site
        self.keep_flags = set()                         # flag ids made without the clear attribute
        self.log = []
        self.slept_ms = 0
        st = sc.stub
        st(0x7E449030, self.ev_set, "OlyEvSt")
        st(0x7E449083, self.ev_set, "OlyEvSt (irq)")
        st(0x7E4490AF, self.ev_wait, "OlyEvWt")
        st(0x7E449175, self.ev_clear, "OlyEvCl")
        st(0x7E434E26, self.ev_ref, "flag reference")
        st(0x7E449218, self.q_read, "OlyQeRd")
        st(0x7E4492B9, self.q_write, "OlyQeWr")
        st(0x7E434EF2, self.q_count, "queue count")
        for a, n in ((0x7E436343, "dtq send"), (0x7E433EFE, "dtq send (poll)"), (0x7E431BBC, "dtq send (irq)")):
            st(a, self.dtq_send, n)
        st(0x7E434B00, self.dtq_recv, "dtq receive")
        st(0x7E437192, self.dtq_trecv, "dtq receive (timeout)")
        st(0x7E449409, self.sem_wait, "OlySmWt")
        st(0x7E4494A1, self.sem_signal, "OlySmSi")
        st(0x7E4494E9, self.sem_signal, "OlySmSi (irq)")
        st(0x7E449605, self.sleep, "OlyTaSS")
        for a, n in ((0x7E449541, "OlyTaSt"), (0x7E44958D, "OlyTaSp"), (0x7E4495D9, "OlyTaWu")):
            st(a, self.task_op(n), n)
        st(0x7E4650A2, self.timer_start, "timer start")
        st(0x7E4650DD, self.timer_stop, "timer stop")
        self.timers, self._next_timer = {}, 1

    # --- helpers
    def _id(self, g):
        v = g["d0"] & 0xFFFF
        return v - 0x10000 if v & 0x8000 else v

    def _note(self, *a):
        self.log.append((self.sc.current.name if self.sc.current else "?",) + a)

    def _wait(self, kind, oid, tmo, detail="", ptn=0):
        """What a wait does when the object is not ready."""
        if tmo == 0:
            self._note(kind, oid, "poll: not ready")
            return {"d0": TIMEOUT}
        t = self.sc.current
        if t is not None and t.stack_size:              # a task made with sc.task: park it
            self._note(kind, oid, "block", detail)
            t.wait = (kind, oid, ptn)
            return BLOCK
        raise Stuck("%s %d %s: nothing supplies it (set os.auto[(%r, %d)] or make it ready before the call)"
                    % (kind, oid, detail, kind, oid))

    def ready(self, t):
        """True when task t can go on: not started yet, or the object it waits for is ready."""
        if t.done or getattr(t, "faulted", False):
            return False
        if not t.started or t.blocked is None:
            return True
        kind, oid, ptn = getattr(t, "wait", (None, 0, 0))
        if kind == "flag":
            return bool(self.flags.get(oid, 0) & ptn)
        if kind == "queue":
            return bool(self.queues.get(oid))
        if kind == "dtq":
            return bool(self.dtqs.get(oid))
        if kind == "sem":
            return self.sems.get(oid, 1) > 0
        return False

    def schedule(self, tasks, max_runs=50, on_result=None, **kw):
        """Run the ready tasks, first in the list first (give the list in priority order), until none is ready.
        No pre-emption: a task runs until it waits. Returns the list of results. Stops at the first fault."""
        out = []
        for _ in range(max_runs):
            t = next((t for t in tasks if self.ready(t)), None)
            if t is None:
                break
            r = self.sc.run(t, label="%s #%d" % (t.name, len(out)), **kw)
            r.task = t.name
            out.append(r)
            if on_result:
                on_result(r)
            if r.fault:
                t.faulted = True
                break
        return out

    # --- event flags
    def ev_set(self, sc, g):
        i = self._id(g)
        self.flags[i] = self.flags.get(i, 0) | g["d1"]
        self._note("flag", i, "set 0x%X -> 0x%X" % (g["d1"], self.flags[i]))
        return {"d0": 0}

    def ev_clear(self, sc, g):
        i = self._id(g)
        self.flags[i] = self.flags.get(i, 0) & g["d1"]
        self._note("flag", i, "clear with mask 0x%X -> 0x%X" % (g["d1"], self.flags[i]))
        return {"d0": 0}

    def ev_ref(self, sc, g):
        i = self._id(g)
        sc.w32(g["a0"] + 4, self.flags.get(i, 0))
        return {"d0": 0}

    def ev_wait(self, sc, g):
        i, ptn = self._id(g), g["d1"]
        tmo = sc.stack_arg(g, 0)
        cur = self.flags.get(i, 0)
        if not cur & ptn and g["mdr"] in self.auto_sites:      # a wait from a listed call site (e.g. "job done")
            self.auto[("flag", i)] = self.auto_sites[g["mdr"]]
        if not cur & ptn and ("flag", i) in self.auto:
            bits = self.auto[("flag", i)]
            bits = bits(ptn) if callable(bits) else bits
            cur = self.flags[i] = cur | (bits & ptn if bits else 0)
            self._note("flag", i, "auto-set 0x%X for wait 0x%X" % (bits, ptn))
        if cur & ptn:
            if g["a0"]:
                sc.w32(g["a0"], cur)
            self._note("flag", i, "wait 0x%X met by 0x%X" % (ptn, cur))
            if i not in self.keep_flags:                # TA_CLR: the kernel clears the whole pattern (0x7E437870)
                self.flags[i] = 0
            return {"d0": 0}
        return self._wait("flag", i, tmo, "wait 0x%X (now 0x%X)" % (ptn, cur), ptn)

    # --- message queues
    def q_write(self, sc, g):
        i = self._id(g)
        ptr, size = sc.r32(g["a0"]), sc.r32(g["a0"] + 4)
        msg = sc.read(ptr, size)
        self.queues.setdefault(i, deque()).append(msg)
        self._note("queue", i, "write " + msg.hex())
        return {"d0": 0}

    def q_read(self, sc, g):
        i, tmo = self._id(g), g["d1"]
        q = self.queues.setdefault(i, deque())
        if not q and ("queue", i) in self.auto:
            q.append(self.auto[("queue", i)])
        if q:
            msg = q.popleft()
            sc.write(sc.r32(g["a0"]), msg)
            self._note("queue", i, "read " + msg.hex())
            return {"d0": 0}
        return self._wait("queue", i, tmo, "read")

    def q_count(self, sc, g):
        i = self._id(g)
        sc.w32(g["a0"] + 4, len(self.queues.get(i, ())))
        return {"d0": 0}

    def post(self, qid, msg):
        """Put a message on a queue from the scenario (as another task would)."""
        self.queues.setdefault(qid, deque()).append(bytes(msg))

    # --- data queues (one word per item)
    def dtq_send(self, sc, g):
        i = self._id(g)
        self.dtqs.setdefault(i, deque()).append(g["d1"])
        self._note("dtq", i, "send 0x%08X" % g["d1"])
        return {"d0": 0}

    def _dtq_take(self, sc, g, tmo):
        i = self._id(g)
        q = self.dtqs.setdefault(i, deque())
        if not q and ("dtq", i) in self.auto:
            q.append(self.auto[("dtq", i)])
        if q:
            v = q.popleft()
            sc.w32(g["a0"], v)
            self._note("dtq", i, "receive 0x%08X" % v)
            return {"d0": 0}
        return self._wait("dtq", i, tmo, "receive")

    def dtq_recv(self, sc, g):
        return self._dtq_take(sc, g, -1)

    def dtq_trecv(self, sc, g):
        return self._dtq_take(sc, g, g["d1"])

    # --- semaphores
    def sem_wait(self, sc, g):
        i, tmo = self._id(g), g["d1"]
        n = self.sems.get(i, 1)
        if n == 0 and self.auto.get(("sem", i)):
            n = 1
        if n > 0:
            self.sems[i] = n - 1
            self._note("sem", i, "wait: taken")
            return {"d0": 0}
        return self._wait("sem", i, tmo, "wait")

    def sem_signal(self, sc, g):
        i = self._id(g)
        self.sems[i] = self.sems.get(i, 1) + 1
        self._note("sem", i, "signal -> %d" % self.sems[i])
        return {"d0": 0}

    # --- software timers (driver 0x7E4650A2 / 0x7E4650DD): kept here, fired by the scenario
    def timer_start(self, sc, g):
        h = self._next_timer
        self._next_timer += 1
        self.timers[h] = (g["d0"] & 0xFFFF, g["d1"] & 0xFFFF, g["a0"], g["a1"])
        self._note("timer", h, "start mode %d, %d ms, callback 0x%08X(0x%08X)" % self.timers[h])
        return {"d0": h}

    def timer_stop(self, sc, g):
        h = g["d1"] & 0xFFFF
        self._note("timer", h, "stop" if h in self.timers else "stop (not running)")
        self.timers.pop(h, None)
        return {"d0": 0}

    def fire_timers(self, **kw):
        """Call the callback of every running timer once, as the timer interrupt would, and drop the timer
        (cyclic modes are not kept). Returns the results."""
        out = []
        for h in sorted(self.timers):
            mode, ms, cb, arg = self.timers.pop(h)
            self.log.append(("timer", "timer", h, "fire 0x%08X(0x%08X) after %d ms" % (cb, arg, ms)))
            out.append(self.sc.call(cb, {"a0": arg, "d0": arg}, frame=(0, 0), label="timer %d callback 0x%08X" % (h, cb), **kw))
        return out

    # --- tasks
    def sleep(self, sc, g):
        self.slept_ms += g["d0"]
        self._note("sleep", g["d0"])
        return {"d0": 0}

    def task_op(self, name):
        def fn(sc, g):
            self._note(name, self._id(g))
            return {"d0": 0}
        return fn


def install(sc):
    sc.os = OSModel(sc)
    return sc.os
