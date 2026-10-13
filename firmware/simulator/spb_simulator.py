#!/usr/bin/env python3
# ===========================================================================
# SPB - control board simulator
#
# Runs on a PC and talks to the display panel through a USB-serial adapter.
# It lets you test the UART protocol (docs/uart-protocol.md) without the
# control board.
#
# ---------------------------------------------------------------------------
# WIRING
#
#   The ESP32-S3 is NOT 5 V tolerant: the adapter must be a 3.3 V one.
#   Most adapters have a 3V3 / 5V jumper: make sure it is on 3.3 V.
#   If you only have a 5 V adapter, put a 2k2 / 3k3 divider to ground on TX.
#
#   Use the 4-pin header H3 of the Waveshare board, which brings out UART0
#   (GPIO43/44). NOT GPIO15/16: those are the SP3485 RS-485 pair and are not
#   available as TTL anywhere.
#
#     adapter TX  ------> H3 pin 3  EX_RXD = GPIO44  (display RX)
#     adapter RX  <------ H3 pin 4  EX_TXD = GPIO43  (display TX)
#     adapter GND ------- H3 pin 2  GND              <- mandatory
#     H3 pin 1 is a 3V3 output: leave it free, do not power it from outside
#     adapter VCC         do NOT connect it: the display has its own supply
#
#   SW1 on the board selects whether GPIO43/44 go to the on-board CH343P
#   USB-serial bridge or to header H3: it must be on the H3 position.
#   Quick check: with the adapter connected and a terminal at 115200, the line
#   "ESP-ROM:esp32s3-..." must appear when the display resets. It is printed by
#   the hardware, whatever the firmware does.
#
# ---------------------------------------------------------------------------
# USAGE
#
#   pip install pyserial
#   python spb_simulator.py             (lists the ports and lets you choose)
#   python spb_simulator.py COM7        (goes straight to that port)
#   python spb_simulator.py COM7 --demo --speed 90
#
#   --demo   slow, realistic curves instead of the fast test waves: pH drifts up
#            and is pulled back by an acid dose, ORP follows the chlorine dose,
#            the water warms and cools over a day, the flow is steady.
#   --speed  how much faster than real time the demo runs (default 1). With
#            --speed 90 one real second is 90 simulated seconds, so a chart of
#            240 samples taken every 2 s (trend_interval_s in spb-display.yaml)
#            shows about 12 simulated hours in 8 minutes: good for a video.
#
#   Then press 'h' for the keyboard commands.
#
#   python spb_simulator.py --selftest   internal test, no serial port needed
#
# WHAT IT SIMULATES (same frames and rules as the real board)
#   S status every 500 ms, P parameters + calibration every 2 s and after every
#   settings command, G filtration schedule every 2 s and after every set, A
#   replies to the C commands. The accept/reject rules and ranges are those of
#   control-link-display.yaml, control-settings.yaml and control-schedule.yaml;
#   the rejection reasons are in English, as the real board sends them (the
#   display translates them itself when it is set to Italian).
# ===========================================================================


import sys
import time
import math
import datetime

BAUD = 115200
PERIOD_S = 0.5            # one status frame every 500 ms

# ---- parameters as on the control board (spb-control.yaml) -----------------
FREQ_MIN, FREQ_MAX, FREQ_NORMAL = 25.0, 50.0, 42.0
FLOW_MAIN, FLOW_CELL = 5.0, 0.3
MISMATCH_PH, MISMATCH_ORP = 0.30, 40.0
DP_BACKWASH = 0.50
JOG_MAX_S = 60
CAL_PH_REF, CAL_ORP_REF = -3.5, 1000.0
CAL_MIN_DV, CAL_MAX_INSTAB = 0.020, 0.005
CAL_SLOPE_MIN, CAL_SLOPE_MAX = 0.4, 2.5
BACKWASH_S = (10, 120, 30)          # pump stop, wash, rinse

# Filtration minutes per program / mode / (Mon-Fri, Sat-Sun): same table as the board
HOURS = [[(0, 0), (0, 0), (0, 0)],
         [(480, 480), (300, 300), (180, 180)],     # daily: high, normal, gentle
         [(420, 600), (300, 480), (180, 300)],     # weekly
         [(240, 240), (180, 180), (120, 120)]]     # winter

# The "real" electrode (the voltage the board would read) is slightly different
# from the reference line, so a fresh board reads wrong until it is calibrated.
ELECTRODE = {"ph": (-3.4, 11.8), "orp": (960.0, 10.0)}


def checksum(body: str) -> str:
    """XOR of all characters before the asterisk, last '|' included."""
    x = 0
    for c in body.encode("ascii"):
        x ^= c
    return "%02X" % x


def frame(body: str, bad: bool = False) -> bytes:
    ck = checksum(body)
    if bad:                                     # deliberately wrong checksum
        ck = "%02X" % ((int(ck, 16) ^ 0xFF) & 0xFF)
    return (body + "*" + ck + "\n").encode("ascii")


def field(msg: str, key: str):
    k = "|" + key + "="
    p = msg.find(k)
    if p < 0:
        return None
    p += len(k)
    e = msg.find("|", p)
    if e < 0:
        e = msg.find("*", p)
    return msg[p:e] if e > 0 else None


def parse(line: str):
    """Returns (type, {field: value}) or None if the checksum does not match."""
    line = line.strip()
    st = line.rfind("*")
    if len(line) < 6 or st < 0 or len(line) < st + 3:
        return None
    if line[st + 1:st + 3].upper() != checksum(line[:st]):
        return None
    fields = {}
    for part in line[:st].split("|")[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    return line[0], fields


# --------------------------------------------------------------------------
# Simulated plant state
# --------------------------------------------------------------------------
class Plant:
    def __init__(self, demo=False, speed=1.0):
        self.demo = demo
        self.speed = speed
        self.t0 = time.time()
        self.mode = "A"            # A = AUTO, M = MANUAL, 0 = ZERO
        self.pump = True
        self.alarms = 0
        self.orp2_valid = True
        self.tanks_full = True
        self.values_frozen = False
        self.hz_offset = 0.0
        self.ev = "0000"           # ev4 = pool lighting
        self.scenario = "norm"
        self.blackout_until = 0.0
        self.t_frozen = 0.0
        self.scen_ok = True
        # live parameters (control-settings.yaml)
        self.fp, self.fc, self.dp, self.do_, self.fn = (
            FLOW_MAIN, FLOW_CELL, MISMATCH_PH, MISMATCH_ORP, FREQ_NORMAL)
        self.dl = DP_BACKWASH
        # calibration: line value = m*V + q. Starts valid and exact so the demo
        # looks normal; key 'u' invalidates it to try the calibration page.
        self.cal = {"ph": {"m": ELECTRODE["ph"][0], "q": ELECTRODE["ph"][1], "ok": True, "pend": None},
                    "orp": {"m": ELECTRODE["orp"][0], "q": ELECTRODE["orp"][1], "ok": True, "pend": None}}
        self.v_avg = {"ph": None, "orp": None}
        self.bath = None           # None | ("ph", value) | ("orp", value)
        self.backwash_end = 0.0
        self.backwash_phase = 0
        self.n_rx = self.n_rejected = 0
        # filtration schedule (control-schedule.yaml), minutes from midnight
        self.g = {"pr": 0, "mo": 1, "fv": 0, "sh": 0, "in": 480, "fi": 1320, "vi": 480, "vf": 1140}
        self.g_acc_s = 0.0
        self.g_day = None
        self.g_run = False
        self.g_st = 0
        self.g_tg = 0

    def t(self):
        if self.values_frozen:
            return self.t_frozen
        self.t_frozen = time.time() - self.t0
        return self.t_frozen

    # ---- the signals of the plant (true values, before the probe model) --------
    def signals(self):
        t = self.t()
        if self.demo:
            s = t * self.speed                       # simulated seconds
            cycle = (s % 2400.0) / 2400.0            # 40 simulated minutes
            ph = 7.05 + 0.40 * cycle + 0.02 * math.sin(s / 170.0)
            ps = ph + 0.03 * math.sin(s / 90.0)
            orp = 690.0 - 35.0 * cycle + 18.0 * math.sin(s / 2300.0) + 4.0 * math.sin(s / 61.0)
            tv = 26.0 + 2.0 * math.sin(2.0 * math.pi * s / 86400.0 - 1.2)
            tc = tv - 0.6 + 0.1 * math.sin(s / 300.0)
            hz = 42.0 + 0.3 * math.sin(s / 700.0) + self.hz_offset
            cu = 61.0 + 1.5 * math.sin(s / 500.0)
            q1 = 12.4 + 0.3 * math.sin(s / 400.0)
            q2 = 0.55 + 0.02 * math.sin(s / 250.0)
            l1 = 74.0 - (s / 3600.0) % 20.0
            l2 = 61.0 - (s / 5400.0) % 15.0
            dpf = 0.22 + 0.36 * ((s / 21600.0) % 1.0)   # filter clogs over 6 simulated hours
        else:
            ph = 7.2 + 0.35 * math.sin(t / 9.0)
            ps = ph + 0.04 * math.sin(t / 3.0)
            orp = 700.0 + 45.0 * math.sin(t / 13.0)
            tv = 26.5 + 1.2 * math.sin(t / 40.0)
            tc = tv - 0.6 + 0.2 * math.sin(t / 11.0)      # cell, always a bit lower
            hz = 42.0 + 1.5 * math.sin(t / 7.0) + self.hz_offset
            cu = 61.0 + 4.0 * math.sin(t / 5.0)
            q1 = 12.4 + 0.8 * math.sin(t / 6.0)
            q2 = 0.55 + 0.05 * math.sin(t / 4.0)
            l1 = 74.0 - (t / 30.0) % 20.0
            l2 = 61.0 - (t / 45.0) % 15.0
            dpf = 0.25 + 0.30 * (0.5 + 0.5 * math.sin(t / 60.0))
        return dict(ph=ph, ps=ps, orp=orp, os=(orp - 12.0) if self.orp2_valid else None,
                    tv=tv, tc=tc, hz=hz, cu=cu, q1=q1, q2=q2, l1=l1, l2=l2, l3=88.0, dpf=dpf)

    # ---- primary probe model: electrode volts -> board reading ------------------
    def probe_value(self, probe):
        if self.bath and self.bath[0] == probe:
            return self.bath[1]
        return self.signals()["ph" if probe == "ph" else "orp"]

    def volt(self, probe):
        m, q = ELECTRODE[probe]
        return (self.probe_value(probe) - q) / m

    def reading(self, probe):
        c = self.cal[probe]
        return c["m"] * self.volt(probe) + c["q"]

    def pumping(self):
        return self.pump and self.backwash_end == 0

    # ---- the 13 dosing permissives, as on the board ----------------------------
    def permissives(self):
        sg = self.signals()
        ph, orp = self.reading("ph"), self.reading("orp")
        pu = self.pumping()
        return [pu,
                pu and sg["q1"] >= self.fp,
                pu and sg["q2"] >= self.fc,
                0 < ph < 14,
                -1000 < orp < 1500,
                sg["os"] is not None and abs(ph - sg["ps"]) <= self.dp,
                sg["os"] is not None and abs(orp - sg["os"]) <= self.do_,
                self.cal["ph"]["ok"],
                self.cal["orp"]["ok"],
                self.tanks_full,
                self.alarms == 0,
                self.backwash_end == 0,
                self.mode == "A"]

    def tick(self, dt):
        """Called from the main loop with the time elapsed since the last call."""
        now = time.time()
        if self.backwash_end and now >= self.backwash_end:
            self.backwash_phase += 1
            if self.backwash_phase >= len(BACKWASH_S):
                self.backwash_end = 0.0
                self.backwash_phase = 0
                self.pump = True
            else:
                self.backwash_end = now + BACKWASH_S[self.backwash_phase]
        for p in ("ph", "orp"):
            v = self.volt(p)
            self.v_avg[p] = v if self.v_avg[p] is None else self.v_avg[p] * 0.9 + v * 0.1
        self._schedule(dt)

    def target_for_day(self, dow):
        g = self.g
        return HOURS[g["pr"]][g["mo"]][1 if dow >= 5 else 0]

    def _schedule(self, dt):
        """Same logic as the 1 s interval of control-schedule.yaml, with the PC clock."""
        t = datetime.datetime.now()
        if self.g_day != t.timetuple().tm_yday:
            self.g_day = t.timetuple().tm_yday
            self.g_acc_s = 0.0
        if self.pumping():
            self.g_acc_s += dt
        g = self.g
        tgt = self.target_for_day(t.weekday())
        self.g_tg = tgt
        now_min = t.hour * 60 + t.minute
        ini, fin = (g["vi"], g["vf"]) if g["fv"] else (g["in"], g["fi"])
        if ini == fin:
            in_window = False
        elif ini < fin:
            in_window = ini <= now_min < fin
        else:
            in_window = now_min >= ini or now_min < fin
        auto_ok = self.mode == "A" and self.backwash_end == 0
        if g["sh"]:
            self.g_st = 7 if auto_ok else 4
            self.g_tg = 1440
        elif g["pr"] == 0:
            self.g_st = 0
        elif not auto_ok:
            self.g_st = 4
        elif tgt <= 0:
            self.g_st = 6
        elif self.g_acc_s >= tgt * 60:
            self.g_st = 3
        elif not in_window:
            self.g_st = 1
        else:
            self.g_st = 2
        if not auto_ok:
            self.g_run = False
            return
        wanted = self.g_st in (2, 7)
        if wanted and not self.g_run:
            self.hz_offset = self.fn - FREQ_NORMAL
            self.pump = True
            self.g_run = True
            print("schedule: pump start")
        elif not wanted and self.g_run:
            self.pump = False
            self.g_run = False
            print("schedule: pump stop")

    # ---- frames ------------------------------------------------------------------
    def status_body(self) -> str:
        sg = self.signals()
        pu = self.pumping()
        ph, orp = self.reading("ph"), self.reading("orp")
        perm = self.permissives()
        ok = all(perm)
        f = 1 if self.tanks_full else 0
        dpf = sg["dpf"]
        return (
            "S|mo={mo}|tv={tv:.1f}|tc={tc:.1f}|ph={ph:.2f}|ps={ps:.2f}"
            "|or={orp:.0f}|os={os:.0f}"
            "|hz={hz:.1f}|cu={cu:.1f}|pu={pu}|q1={q1:.1f}|q2={q2:.1f}"
            "|l1={l1:.0f}|l2={l2:.0f}|l3={l3:.0f}|f1={f}|f2={f}|f3={f}"
            "|ev={ev}|do={do}|cs={cs}|al={al}"
            "|cb={cb}|pa={pa:.2f}|pb={pb:.2f}|dd={dd:.2f}|lc={lc}|dt={dt}|"
        ).format(mo=self.mode, tv=sg["tv"], tc=sg["tc"], ph=ph, ps=sg["ps"], orp=orp,
                 os=sg["os"] if sg["os"] is not None else -999.0,
                 hz=sg["hz"] if pu else 0.0, cu=sg["cu"] if pu else 0.0, pu=1 if pu else 0,
                 q1=sg["q1"] if pu else 0.0, q2=sg["q2"] if pu else 0.0,
                 l1=sg["l1"], l2=sg["l2"], l3=sg["l3"], f=f, ev=self.ev,
                 do=1 if ok else 0, cs=sum(1 for c in perm if c), al=self.alarms,
                 cb="".join("1" if c else "0" for c in perm),
                 pa=1.8 if pu else 0.0, pb=(1.8 - dpf) if pu else 0.0, dd=dpf if pu else 0.0,
                 lc=1 if (pu and dpf >= self.dl) else 0,
                 dt=datetime.datetime.now().strftime("%Y%m%d%H%M"))

    def frame_p(self) -> bytes:
        now = time.time()
        for s in ("ph", "orp"):
            p = self.cal[s]["pend"]
            if p and now - p[2] > 600:
                self.cal[s]["pend"] = None
        cp, co = self.cal["ph"], self.cal["orp"]
        vp, vo = self.v_avg["ph"], self.v_avg["orp"]
        body = ("P|fp=%.2f|fc=%.2f|dp=%.2f|do=%.0f|fn=%.1f|vp=%.4f|vo=%.4f|cp=%d|co=%d"
                "|np=%d|bp=%.2f|no=%d|bo=%.0f|mp=%.3f|mr=%.3f|dl=%.2f|") % (
            self.fp, self.fc, self.dp, self.do_, self.fn,
            -999.0 if vp is None else vp, -999.0 if vo is None else vo,
            cp["ok"], co["ok"],
            1 if cp["pend"] else 0, cp["pend"][1] if cp["pend"] else 0.0,
            1 if co["pend"] else 0, co["pend"][1] if co["pend"] else 0.0,
            cp["m"], co["m"], self.dl)
        return frame(body)

    def frame_g(self) -> bytes:
        g = self.g
        body = ("G|pr=%d|mo=%d|fv=%d|sh=%d|in=%d|fi=%d|vi=%d|vf=%d"
                "|h0=%d|h1=%d|h2=%d|h3=%d|h4=%d|h5=%d|h6=%d|ac=%d|tg=%d|st=%d|") % (
            g["pr"], g["mo"], g["fv"], g["sh"], g["in"], g["fi"], g["vi"], g["vf"],
            *[self.target_for_day(d) for d in range(7)],
            int(self.g_acc_s // 60), self.g_tg, self.g_st)
        return frame(body)

    # ---- commands: same rules as control-link-display.yaml -----------------------
    def evaluate_command(self, cmd: str, val: str):
        """Returns (ok, reason)."""
        manual = self.mode == "M"
        if self.mode == "0":
            return False, "selector in ZERO"
        if self.backwash_end and cmd != "back":
            return False, "procedure in progress"
        if cmd == "ackal":
            self.alarms = 0
            return True, ""
        if cmd == "hz":
            try:
                f = float(val)
            except ValueError:
                return False, "invalid value"
            if not (FREQ_MIN <= f <= FREQ_MAX):
                return False, "frequency out of range"
            self.hz_offset = f - FREQ_NORMAL
            return True, ""
        if cmd == "scen":
            # Not implemented on the real board (it answers "unknown command").
            # Accepted here by default so the scenario buttons can be tried.
            if not self.scen_ok:
                return False, "unknown command"
            if val not in ("norm", "int", "sil", "risc", "gioco", "gelo", "heat", "play", "frost"):
                return False, "invalid value"
            self.scenario = val
            return True, ""
        if cmd == "pump":
            if not manual:
                return False, "selector not in MANUAL"
            self.pump = (val == "1")
            if self.pump:
                self.hz_offset = self.fn - FREQ_NORMAL
            return True, ""
        if cmd.startswith("ev"):
            if not manual:
                return False, "selector not in MANUAL"
            if cmd in ("ev1", "ev2", "ev3", "ev4"):
                i = int(cmd[2]) - 1
                e = list(self.ev)
                e[i] = "1" if val == "1" else "0"
                self.ev = "".join(e)
                return True, ""
            return False, "unknown valve"
        if cmd == "filt":
            if not manual:
                return False, "selector not in MANUAL"
            return True, ""
        if cmd in ("dosa", "dosc", "dosr"):
            try:
                sec = int(val)
            except ValueError:
                sec = 0
            names = {"dosa": "acid", "dosc": "chlorine", "dosr": "reserve"}
            if not manual:
                return False, "selector not in MANUAL"
            if sec < 1 or sec > 60:
                return False, "duration out of range"
            if not self.tanks_full:
                return False, "%s drum empty" % names[cmd]
            print("   [dosing %s for %d s]" % (names[cmd], min(sec, JOG_MAX_S)))
            return True, ""
        if cmd == "back":
            if not manual:
                return False, "selector not in MANUAL"
            if val == "1":
                self.pump = False
                self.backwash_phase = 0
                self.backwash_end = time.time() + BACKWASH_S[0]
            else:
                self.backwash_end = 0.0
            return True, ""
        if cmd == "set":
            return self._set(val)
        if cmd == "rst":
            if val != "par":
                return False, "unknown reset"
            self.fp, self.fc, self.dp, self.do_, self.fn = (
                FLOW_MAIN, FLOW_CELL, MISMATCH_PH, MISMATCH_ORP, FREQ_NORMAL)
            self.dl = DP_BACKWASH
            return True, ""
        if cmd == "calc":
            if val == "p":
                self.cal["ph"]["pend"] = None
            elif val == "o":
                self.cal["orp"]["pend"] = None
            else:
                return False, "unknown probe"
            return True, ""
        if cmd in ("calp", "calo"):
            return self._cal("ph" if cmd == "calp" else "orp", val, manual)
        return False, "unknown command"

    def _set(self, val):
        if ":" not in val:
            return False, "invalid value"
        key, num = val.split(":", 1)
        try:
            x = float(num)
        except ValueError:
            return False, "invalid value"
        lim = {"fp": (0, 100), "fc": (0, 20), "dp": (0.05, 2.0), "do": (5, 300),
               "fn": (FREQ_MIN, FREQ_MAX), "dl": (0.1, 3.0)}
        if key.startswith("g") and len(key) == 3:
            return self._set_g(key, x)
        if key not in lim:
            return False, "unknown parameter"
        lo, hi = lim[key]
        if x < lo or x > hi:
            return False, "frequency out of range" if key == "fn" else "value out of range"
        setattr(self, "do_" if key == "do" else key, x)
        return True, ""

    def _set_g(self, key, x):
        lim = {"gpr": ("pr", 3), "gmo": ("mo", 2), "gfv": ("fv", 1), "gsh": ("sh", 1),
               "gin": ("in", 1439), "gfi": ("fi", 1439), "gvi": ("vi", 1439), "gvf": ("vf", 1439)}
        if key not in lim:
            return False, "unknown parameter"
        name, hi = lim[key]
        if x < 0 or x > hi:
            return False, "value out of range"
        self.g[name] = int(round(x))
        return True, ""

    def _cal(self, s, val, manual):
        try:
            buf = float(val)
        except ValueError:
            return False, "invalid buffer value"
        if not manual:
            return False, "selector not in MANUAL"
        if (s == "ph" and not 1 <= buf <= 13) or (s == "orp" and not -500 <= buf <= 1200):
            return False, "buffer out of range"
        vavg, vraw = self.v_avg[s], self.volt(s)
        if vavg is None:
            return False, "probe has no reading"
        if abs(vraw - vavg) > CAL_MAX_INSTAB:
            return False, "unstable reading"
        c = self.cal[s]
        now = time.time()
        if c["pend"] and now - c["pend"][2] > 600:
            c["pend"] = None
        if not c["pend"]:
            c["pend"] = (vavg, buf, now)          # first point: nothing changes yet
            return True, ""
        pv, pb, _ = c["pend"]
        if abs(buf - pb) < (1.0 if s == "ph" else 50.0):
            return False, "buffer same as first point"
        if abs(vavg - pv) < CAL_MIN_DV:
            return False, "voltage same as first point"
        m = (buf - pb) / (vavg - pv)
        q = buf - m * vavg
        ref = CAL_PH_REF if s == "ph" else CAL_ORP_REF
        if not CAL_SLOPE_MIN <= m / ref <= CAL_SLOPE_MAX:
            c["pend"] = None
            return False, "abnormal slope"
        c.update(m=m, q=q, ok=True, pend=None)
        return True, ""


def handle_line(plant: Plant, line: str):
    """Handle a line received from the panel. Returns the frames to send back."""
    r = parse(line)
    if r is None or r[0] != "C":
        return []
    c = r[1]
    plant.n_rx += 1
    n, cmd, val = c.get("n", "0"), c.get("c", ""), c.get("v", "")
    ok, why = plant.evaluate_command(cmd, val)
    if not ok:
        plant.n_rejected += 1
    print("<- C n=%s c=%s v=%s   ->  %s" % (n, cmd, val, "ok" if ok else "ERR " + why))
    reply = "A|n=%s|r=ok|" % n if ok else "A|n=%s|r=err|w=%s|" % (n, why)
    out = [frame(reply)]
    if cmd in ("set", "rst", "calp", "calo", "calc"):
        out.append(plant.frame_p())
    if cmd == "set":
        out.append(plant.frame_g())
    return out


HELP = """
  a / m / z   selector in AUTO / MANUAL / ZERO
  p           pump running  on/off
  x           alarm active  on/off
  n           secondary ORP probe valid / invalid (-999)
  v           floats: tanks full / empty
  f           freeze the values (useful to read the screen calmly)
  b           5 s blackout: stops transmitting
  !           send ONE frame with a wrong checksum (the display must ignore it)
  u           invalidate both calibrations (to try the calibration page)
  k           probe bath: pool -> pH 7.00 -> pH 4.00 -> ORP 225 -> ORP 470 -> pool
  s           accept / reject the "scen" commands (unknown on the real board)
  d           dump: print everything arriving on the serial line, even garbage
  h           this help
  q           quit
"""
BATHS = [None, ("ph", 7.0), ("ph", 4.0), ("orp", 225.0), ("orp", 470.0)]


def choose_port():
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    if not ports:
        print("No serial port found.")
        sys.exit(1)
    print("\nAvailable ports:")
    for i, p in enumerate(ports):
        print("  [%d] %s  %s" % (i, p.device, p.description))
    while True:
        s = input("\nWhich one? (number, or a name like COM7): ").strip()
        if s.isdigit() and int(s) < len(ports):
            return ports[int(s)].device
        if s:
            return s


def main():
    try:
        import serial
    except ImportError:
        print("pyserial is missing.  Install it with:  pip install pyserial")
        sys.exit(1)
    try:
        import msvcrt          # Windows: single keys without pressing Enter
        def read_key():
            return msvcrt.getch().decode("ascii", "ignore").lower() if msvcrt.kbhit() else None
    except ImportError:
        import select          # Linux / macOS
        def read_key():
            r, _, _ = select.select([sys.stdin], [], [], 0)
            return sys.stdin.readline().strip()[:1].lower() if r else None

    args = sys.argv[1:]
    demo = "--demo" in args
    speed = 1.0
    if "--speed" in args:
        try:
            speed = float(args[args.index("--speed") + 1])
        except (IndexError, ValueError):
            print("--speed needs a number, for example --speed 90")
            sys.exit(1)
    pos = [a for i, a in enumerate(args)
           if not a.startswith("--") and not (i > 0 and args[i - 1] == "--speed")]
    port = pos[0] if pos else choose_port()
    try:
        ser = serial.Serial(port, BAUD, timeout=0)
    except Exception as e:
        print("Cannot open %s: %s" % (port, e))
        sys.exit(1)

    plant = Plant(demo=demo, speed=speed)
    buf = ""
    next_s = next_p = 0.0
    n_sent = n_discarded = n_byte = last_n_byte = 0
    bath_i = 0
    t_prev = time.time()
    next_beat = time.time() + 5.0
    dump = True                 # print everything at first: useful for bring-up

    print("\nPort %s opened at %d baud." % (port, BAUD))
    print("The display should switch to 'connected' within a couple of seconds.")
    print("If it does not, see the LOOPBACK TEST below.")
    print("""
  LOOPBACK TEST (do this if the display stays silent)
    Unplug the two wires from the display and join TX and RX of the adapter.
    Below you must see RAW lines with the frames coming back: if you do,
    adapter, port and driver work and the problem is in the connection to the
    display. If you do not, it is the adapter or the port.""")
    print(HELP)

    try:
        while True:
            now_s = time.time()
            plant.tick(now_s - t_prev)
            t_prev = now_s

            # ---- send status, parameters and schedule ------------------
            if now_s >= plant.blackout_until:
                if now_s >= next_s:
                    next_s = now_s + PERIOD_S
                    body = plant.status_body()
                    ser.write(frame(body))
                    n_sent += 1
                    if n_sent % 4 == 1:          # one line every two seconds
                        print("TX  " + body[:96] + ("..." if len(body) > 96 else ""))
                if now_s >= next_p:
                    next_p = now_s + 2.0
                    ser.write(plant.frame_p())
                    ser.write(plant.frame_g())

            # ---- receive the commands ----------------------------------
            data = ser.read(512)
            if data:
                n_byte += len(data)
                if dump:
                    print("RAW " + repr(data.decode("ascii", "replace")))
                buf += data.decode("ascii", "ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip("\r")
                    if not line:
                        continue
                    if not line.startswith("C"):
                        if dump:
                            print("    (not a command, ignored)")
                        continue
                    print("RX  " + line)
                    if parse(line) is None:
                        n_discarded += 1
                        print("    discarded: checksum missing or wrong")
                        continue
                    for out in handle_line(plant, line):
                        ser.write(out)

            # ---- heartbeat: warn if nothing arrives from the display ---
            if now_s >= next_beat:
                next_beat = now_s + 5.0
                if n_byte == last_n_byte:
                    print("... no byte has arrived from the display yet "
                          "(total received: %d)" % n_byte)
                last_n_byte = n_byte

            # ---- keyboard ----------------------------------------------
            k = read_key()
            if k:
                if k == "q":
                    break
                elif k in ("a", "m", "z"):
                    plant.mode = {"a": "A", "m": "M", "z": "0"}[k]
                    print("--- selector: %s" % {"A": "AUTO", "M": "MANUAL", "0": "ZERO"}[plant.mode])
                elif k == "p":
                    plant.pump = not plant.pump
                    print("--- pump: %s" % ("running" if plant.pump else "stopped"))
                elif k == "x":
                    plant.alarms = 0 if plant.alarms else 1
                    print("--- alarms: %d" % plant.alarms)
                elif k == "n":
                    plant.orp2_valid = not plant.orp2_valid
                    print("--- secondary ORP: %s"
                          % ("valid" if plant.orp2_valid else "NOT valid (-999)"))
                elif k == "v":
                    plant.tanks_full = not plant.tanks_full
                    print("--- tanks: %s" % ("full" if plant.tanks_full else "EMPTY"))
                elif k == "f":
                    plant.values_frozen = not plant.values_frozen
                    print("--- values: %s" % ("frozen" if plant.values_frozen else "moving"))
                elif k == "b":
                    plant.blackout_until = now_s + 5.0
                    print("--- 5 s blackout: the display must notice after 3")
                elif k == "!":
                    ser.write(frame(plant.status_body(), bad=True))
                    print("--- sent a frame with a WRONG checksum: "
                          "the display must ignore it, not update")
                elif k == "u":
                    for s, (m, q) in (("ph", (CAL_PH_REF, 12.0)), ("orp", (CAL_ORP_REF, 0.0))):
                        plant.cal[s].update(m=m, q=q, ok=False, pend=None)
                    print("--- calibrations invalidated: dosing is locked until you calibrate")
                elif k == "k":
                    bath_i = (bath_i + 1) % len(BATHS)
                    plant.bath = BATHS[bath_i]
                    print("--- probe bath: %s" % (plant.bath if plant.bath else "back in the pool"))
                elif k == "s":
                    plant.scen_ok = not plant.scen_ok
                    print("--- scen commands: %s" % ("accepted" if plant.scen_ok else "rejected"))
                elif k == "d":
                    dump = not dump
                    print("--- dump of everything received: %s"
                          % ("on" if dump else "off"))
                elif k == "h":
                    print(HELP)

            time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\nClosed.  Status frames sent: %d   commands received: %d   discarded: %d"
              % (n_sent, plant.n_rx, n_discarded))


def selftest():
    """Internal test: no serial port."""
    plant = Plant()
    fails = 0

    def cmd(c, v, n=1):
        line = "C|n=%d|c=%s|v=%s|" % (n, c, v)
        return b"".join(handle_line(plant, line + "*" + checksum(line))).decode()

    def check(cond, msg):
        nonlocal fails
        if not cond:
            fails += 1
            print("FAILED:", msg)

    def settle(sec=40):
        for _ in range(int(sec * 2)):
            plant.tick(0.5)

    plant.mode = "M"
    plant.values_frozen = True
    settle()
    r = parse(frame(plant.status_body()).decode())
    check(r and r[0] == "S" and r[1]["mo"] == "M" and len(r[1]["cb"]) == 13, "S frame with cb")
    check("pa" in r[1] and "dd" in r[1] and "lc" in r[1] and len(r[1]["dt"]) == 12, "S pressure + clock")
    r = parse(plant.frame_p().decode())
    check(r and r[0] == "P" and r[1]["fp"] == "5.00" and r[1]["dl"] == "0.50", "P frame")
    r = parse(plant.frame_g().decode())
    check(r and r[0] == "G" and r[1]["pr"] == "0", "G frame")
    check(handle_line(plant, "C|n=1|c=pump|v=1|*00") == [], "bad checksum discarded")
    check("r=ok" in cmd("pump", "1"), "pump ok in manual")
    check("r=ok" in cmd("ev4", "1"), "ev4 (lighting) ok")
    check(parse(frame(plant.status_body()).decode())[1]["ev"] == "0001", "ev4 in S frame")
    check("frequency out of range" in cmd("hz", "10"), "hz out of range")
    plant.mode = "A"
    check("selector not in MANUAL" in cmd("pump", "0"), "pump rejected in AUTO")
    check("r=ok" in cmd("set", "fp:7.5") and "fp=7.50" in cmd("set", "fp:7.5"), "set fp + P frame")
    check("pr=2" in cmd("set", "gpr:2"), "weekly program + G frame")
    check("value out of range" in cmd("set", "gpr:4"), "gpr out of range")
    check("h5=480" in cmd("set", "gmo:1"), "weekly normal: Saturday 8 h")
    check("h0=420" in cmd("set", "gmo:0"), "weekly high: Mon-Fri 7 h")
    check("unknown parameter" in cmd("set", "gzz:1"), "unknown g key")
    check("r=err" in cmd("set", "dl:9") and "dl=0.80" in cmd("set", "dl:0.8"), "set dl")
    cmd("rst", "par")
    check("dl=0.50" in plant.frame_p().decode() and "fp=5.00" in plant.frame_p().decode(), "rst")
    cmd("set", "gsh:1")
    check("sh=1" in plant.frame_g().decode(), "shock on")
    check("r=err" in cmd("set", "gsh:2"), "gsh out of range")
    cmd("set", "gsh:0")
    check("value out of range" in cmd("set", "fp:500"), "fp out of range")
    plant.mode = "0"
    check("selector in ZERO" in cmd("pump", "1"), "rejected in ZERO")
    plant.mode = "M"
    plant.scen_ok = False
    check("unknown command" in cmd("scen", "norm"), "scen unknown when disabled")
    plant.tanks_full = False
    check("acid drum empty" in cmd("dosa", "5"), "drum empty")
    plant.tanks_full = True
    check("r=ok" in cmd("back", "1") and plant.backwash_end > 0, "backwash starts")
    check("procedure in progress" in cmd("hz", "40"), "commands blocked during backwash")
    cmd("back", "0")
    # full pH calibration with buffers; the demo calibration is exact, so invalidate it first
    plant.cal["ph"].update(m=CAL_PH_REF, q=12.0, ok=False, pend=None)
    check(not plant.permissives()[7], "pH calibration permissive false when invalid")
    plant.bath = ("ph", 7.0)
    settle()
    check("r=ok" in cmd("calp", "7.00"), "pH first point")
    check(not plant.cal["ph"]["ok"], "first point alone does not validate")
    plant.bath = ("ph", 4.0)
    check("unstable reading" in cmd("calp", "4.00"), "unstable right after bath change")
    settle()
    check("r=ok" in cmd("calp", "4.00"), "pH second point")
    check(plant.cal["ph"]["ok"], "pH calibration valid")
    plant.bath = None
    check(abs(plant.reading("ph") - plant.signals()["ph"]) < 0.05, "pH reading consistent after calibration")
    print("RESULT:", "all ok" if not fails else "%d tests failed" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
