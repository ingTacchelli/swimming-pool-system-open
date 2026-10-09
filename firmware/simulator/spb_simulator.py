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
# ===========================================================================

import sys
import time
import math

try:
    import serial
    from serial.tools import list_ports
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

BAUD = 115200
PERIODO_S = 0.5            # one status frame every 500 ms


# --------------------------------------------------------------------------
# Protocol
# --------------------------------------------------------------------------
def checksum(body: str) -> str:
    """XOR of all characters before the asterisk, last '|' included."""
    x = 0
    for c in body.encode("ascii"):
        x ^= c
    return "%02X" % x


def frame(body: str, guasta: bool = False) -> bytes:
    ck = checksum(body)
    if guasta:                                  # deliberately wrong checksum
        ck = "%02X" % ((int(ck, 16) ^ 0xFF) & 0xFF)
    return (body + "*" + ck + "\n").encode("ascii")


def campo(msg: str, key: str):
    k = "|" + key + "="
    p = msg.find(k)
    if p < 0:
        return None
    p += len(k)
    e = msg.find("|", p)
    if e < 0:
        e = msg.find("*", p)
    return msg[p:e] if e > 0 else None


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
        self.ev = "0000"
        self.scenario = "norm"
        self.blackout_until = 0.0
        self.t_frozen = 0.0

    def t(self):
        if self.values_frozen:
            return self.t_frozen
        self.t_frozen = time.time() - self.t0
        return self.t_frozen

    def status_body(self) -> str:
        t = self.t()
        if self.demo:
            s = t * self.speed                       # simulated seconds
            cycle = (s % 2400.0) / 2400.0            # 40 simulated minutes
            ph = 7.05 + 0.40 * cycle + 0.02 * math.sin(s / 170.0)
            ps = ph + 0.03 * math.sin(s / 90.0)
            orp = 690.0 - 35.0 * cycle + 18.0 * math.sin(s / 2300.0) + 4.0 * math.sin(s / 61.0)
            tv = 26.0 + 2.0 * math.sin(2.0 * math.pi * s / 86400.0 - 1.2)
            tc = tv - 0.6 + 0.1 * math.sin(s / 300.0)
            hz = (42.0 + 0.3 * math.sin(s / 700.0) + self.hz_offset) if self.pump else 0.0
            cu = (61.0 + 1.5 * math.sin(s / 500.0)) if self.pump else 0.0
            q1 = (12.4 + 0.3 * math.sin(s / 400.0)) if self.pump else 0.0
            q2 = (0.55 + 0.02 * math.sin(s / 250.0)) if self.pump else 0.0
            l1 = 74.0 - (s / 3600.0) % 20.0
            l2 = 61.0 - (s / 5400.0) % 15.0
        else:
            ph = 7.2 + 0.35 * math.sin(t / 9.0)
            ps = ph + 0.04 * math.sin(t / 3.0)
            orp = 700.0 + 45.0 * math.sin(t / 13.0)
            tv = 26.5 + 1.2 * math.sin(t / 40.0)
            tc = tv - 0.6 + 0.2 * math.sin(t / 11.0)      # cell, always a bit lower
            hz = (42.0 + 1.5 * math.sin(t / 7.0) + self.hz_offset) if self.pump else 0.0
            cu = (61.0 + 4.0 * math.sin(t / 5.0)) if self.pump else 0.0
            q1 = (12.4 + 0.8 * math.sin(t / 6.0)) if self.pump else 0.0
            q2 = (0.55 + 0.05 * math.sin(t / 4.0)) if self.pump else 0.0
            l1 = 74.0 - (t / 30.0) % 20.0
            l2 = 61.0 - (t / 45.0) % 15.0
        os_ = (orp - 12.0) if self.orp2_valid else -999.0
        l3 = 88.0
        f = 1 if self.tanks_full else 0

        # dosing is enabled only when every condition is fine
        ok = (self.mode == "A" and self.pump and self.tanks_full
              and self.alarms == 0 and self.orp2_valid)
        permissives = 13 if ok else (9 if self.mode != "A" else 11)

        return (
            "S|mo={mo}|tv={tv:.1f}|tc={tc:.1f}|ph={ph:.2f}|ps={ps:.2f}"
            "|or={orp:.0f}|os={os:.0f}"
            "|hz={hz:.1f}|cu={cu:.1f}|pu={pu}|q1={q1:.1f}|q2={q2:.1f}"
            "|l1={l1:.0f}|l2={l2:.0f}|l3={l3:.0f}|f1={f}|f2={f}|f3={f}"
            "|ev={ev}|do={do}|cs={cs}|al={al}|"
        ).format(mo=self.mode, tv=tv, tc=tc, ph=ph, ps=ps, orp=orp, os=os_,
                 hz=hz, cu=cu, pu=1 if self.pump else 0, q1=q1, q2=q2,
                 l1=l1, l2=l2, l3=l3, f=f, ev=self.ev,
                 do=1 if ok else 0, cs=permissives, al=self.alarms)

    def evaluate_command(self, cmd: str, val: str):
        """The same rules the real board applies."""
        if self.mode == "0":
            return False, "selector in ZERO"
        if cmd == "ackal":
            self.alarms = 0
            return True, ""
        if cmd == "hz":
            try:
                f = float(val)
            except ValueError:
                return False, "non-numeric value"
            if not (25.0 <= f <= 50.0):
                return False, "frequency out of range"
            self.hz_offset = f - 42.0
            return True, ""
        if cmd == "scen":
            # The filtration scenario is not a manual operation: it is accepted
            # in AUTO too. ZERO has already been rejected above.
            if val not in ("norm", "int", "sil", "heat", "play", "frost"):
                return False, "unknown scenario"
            self.scenario = val
            return True, ""
        if cmd in ("pump", "filt", "back") or cmd.startswith("ev") or cmd.startswith("dos"):
            if self.mode != "M":
                return False, "selector not in MANUAL"
            if cmd == "pump":
                self.pump = (val == "1")
            elif cmd.startswith("ev") and len(cmd) == 3 and cmd[2].isdigit():
                i = int(cmd[2]) - 1
                if 0 <= i < 4:
                    e = list(self.ev)
                    e[i] = "1" if val == "1" else "0"
                    self.ev = "".join(e)
            elif cmd.startswith("dos"):
                if not self.tanks_full:
                    return False, "tank empty"
            return True, ""
        return False, "unknown command"


AIUTO = """
  a / m / z   selector in AUTO / MANUAL / ZERO
  p           pump running  on/off
  x           alarm active  on/off
  n           secondary ORP probe valid / invalid (-999)
  v           floats: tanks full / empty
  f           freeze the values (useful to read the screen calmly)
  b           5 s blackout: stops transmitting
  !           send ONE frame with a wrong checksum (the display must ignore it)
  d           dump: print everything arriving on the serial line, even garbage
  h           this help
  q           quit
"""


def choose_port():
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
    next_s = 0.0
    n_sent = 0
    n_comandi = 0
    n_discarded = 0
    n_byte = 0
    last_n_byte = 0
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
    print(AIUTO)

    try:
        while True:
            now_s = time.time()

            # ---- send the status ---------------------------------------
            if now_s >= next_s and now_s >= plant.blackout_until:
                next_s = now_s + PERIODO_S
                body = plant.status_body()
                ser.write(frame(body))
                n_sent += 1
                if n_sent % 4 == 1:          # one line every two seconds
                    print("TX  " + body[:96] + ("..." if len(body) > 96 else ""))

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
                    n_comandi += 1
                    print("RX  " + line)
                    st = line.rfind("*")
                    if st < 0 or len(line) < st + 3:
                        n_discarded += 1
                        print("    discarded: checksum missing")
                        continue
                    if line[st + 1:st + 3].upper() != checksum(line[:st]):
                        n_discarded += 1
                        print("    discarded: wrong checksum (expected %s)"
                              % checksum(line[:st]))
                        continue
                    n = campo(line, "n") or "0"
                    c = campo(line, "c") or ""
                    v = campo(line, "v") or ""
                    ok, perche = plant.evaluate_command(c, v)
                    if ok:
                        reply = "A|n=%s|r=ok|" % n
                        print("    accepted")
                    else:
                        reply = "A|n=%s|r=err|w=%s|" % (n, perche)
                        print("    rejected: " + perche)
                    ser.write(frame(reply))

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
                    ser.write(frame(plant.status_body(), guasta=True))
                    print("--- sent a frame with a WRONG checksum: "
                          "the display must ignore it, not update")
                elif k == "d":
                    dump = not dump
                    print("--- dump of everything received: %s"
                          % ("on" if dump else "off"))
                elif k == "h":
                    print(AIUTO)

            time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\nClosed.  Status frames sent: %d   commands received: %d   discarded: %d"
              % (n_sent, n_comandi, n_discarded))


if __name__ == "__main__":
    main()
