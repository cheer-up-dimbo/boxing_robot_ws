"""Session analytics node for BoxBunny.

Computes per-session statistics (punch/pad/impact distributions, fatigue index,
defense rate, movement) and historical trends.  Publishes results as JSON.
"""
from __future__ import annotations
import json, logging, time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from boxbunny_core.constants import SessionState as SSConst, Topics
from boxbunny_msgs.msg import (
    ConfirmedPunch, DefenseEvent, SessionPunchSummary, SessionState,
)

logger = logging.getLogger("boxbunny.analytics")
ANALYTICS_TOPIC = Topics.ANALYTICS_SESSION
FATIGUE_WINDOW_S = 30.0


@dataclass
class _Round:
    start: float = 0.0
    punch_ts: List[float] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    pads: List[str] = field(default_factory=list)
    levels: List[str] = field(default_factory=list)
    forces: List[float] = field(default_factory=list)
    defense: List[Dict[str, Any]] = field(default_factory=list)
    depths: List[float] = field(default_factory=list)
    laterals: List[float] = field(default_factory=list)


@dataclass
class _Session:
    rounds: List[_Round] = field(default_factory=list)
    t0: float = 0.0
    t1: float = 0.0
    n_punches: int = 0
    n_defense: int = 0


class AnalyticsNode(Node):
    """Computes per-session and historical analytics from training data."""

    def __init__(self) -> None:
        super().__init__("analytics_node")
        self.declare_parameter("publish_interval_s", 5.0)
        interval = float(self.get_parameter("publish_interval_s").value)
        self._sess: Optional[_Session] = None
        self._active: bool = False
        self._history: List[Dict[str, Any]] = []
        self._pub = self.create_publisher(String, ANALYTICS_TOPIC, 10)
        self.create_subscription(ConfirmedPunch, Topics.PUNCH_CONFIRMED, self._on_punch, 50)
        self.create_subscription(DefenseEvent, Topics.PUNCH_DEFENSE, self._on_defense, 50)
        self.create_subscription(SessionPunchSummary, Topics.PUNCH_SESSION_SUMMARY, self._on_summary, 10)
        self.create_subscription(SessionState, Topics.SESSION_STATE, self._on_state, 10)
        self.create_timer(interval, self._periodic)
        logger.info("Analytics node initialised")

    # -- Session lifecycle ------------------------------------------------
    def _on_state(self, msg: SessionState) -> None:
        """Track session state transitions."""
        if msg.state == SSConst.ACTIVE and not self._active:
            self._active = True
            if self._sess is None:
                self._sess = _Session(t0=time.time())
            self._sess.rounds.append(_Round(start=time.time()))
        elif msg.state == SSConst.REST:
            self._active = False
        elif msg.state == SSConst.COMPLETE:
            self._active = False
            if self._sess is not None:
                self._sess.t1 = time.time()
                a = self._compute()
                self._publish(a)
                self._history.append(a)
                logger.info("Session analytics published (%d punches)", self._sess.n_punches)
                self._sess = None
        elif msg.state == SSConst.IDLE:
            self._active, self._sess = False, None

    # -- Data collection --------------------------------------------------
    def _on_punch(self, msg: ConfirmedPunch) -> None:
        if self._sess is None or not self._active:
            return
        r = self._rnd()
        if r is None:
            return
        ts = msg.timestamp if msg.timestamp > 0 else time.time()
        r.punch_ts.append(ts)
        r.types.append(msg.punch_type)
        r.pads.append(msg.pad)
        r.levels.append(msg.level)
        r.forces.append(msg.force_normalized)
        self._sess.n_punches += 1

    def _on_defense(self, msg: DefenseEvent) -> None:
        if self._sess is None or not self._active:
            return
        r = self._rnd()
        if r is None:
            return
        r.defense.append({"struck": msg.struck, "type": msg.defense_type, "ts": msg.timestamp})
        self._sess.n_defense += 1

    def _on_summary(self, msg: SessionPunchSummary) -> None:
        """Capture depth/lateral from session summary."""
        r = self._rnd()
        if r is None:
            return
        if msg.avg_depth > 0:
            r.depths.append(msg.avg_depth)
        if msg.lateral_movement > 0:
            r.laterals.append(msg.lateral_movement)

    def _rnd(self) -> Optional[_Round]:
        return self._sess.rounds[-1] if self._sess and self._sess.rounds else None

    # -- Analytics computation --------------------------------------------
    def _compute(self) -> Dict[str, Any]:
        s = self._sess
        if s is None:
            return {}
        all_t, all_p, all_pad, all_lv = [], [], [], []
        all_def: List[Dict] = []
        all_dep: List[float] = []
        all_lat: List[float] = []
        per_round: List[Dict[str, Any]] = []
        for r in s.rounds:
            all_t.extend(r.types)
            all_p.extend(r.pads)
            all_lv.extend(r.levels)
            all_def.extend(r.defense)
            all_dep.extend(r.depths)
            all_lat.extend(r.laterals)
            per_round.append({"punches": len(r.types), "fatigue_index": self._fatigue(r)})
        dur = max(s.t1 - s.t0, 1.0)
        return {
            "total_punches": s.n_punches,
            "punch_distribution": self._dist(all_t),
            "pad_distribution": self._dist(all_p),
            "impact_distribution": self._dist(all_lv),
            "rounds": per_round, "rounds_completed": len(s.rounds),
            "punches_per_minute": round(s.n_punches / (dur / 60), 1),
            "fatigue_index": self._avg_fatigue(s.rounds),
            "defense": self._def_stats(all_def),
            "movement": self._move_stats(all_dep, all_lat),
            "duration_sec": round(dur, 1),
            "trends": self._trends(), "timestamp": time.time(),
        }

    @staticmethod
    def _dist(items: List[str]) -> Dict[str, Any]:
        c: Dict[str, int] = defaultdict(int)
        for i in items:
            if i:
                c[i] += 1
        t = sum(c.values()) or 1
        return {k: {"count": v, "pct": round(v / t * 100, 1)} for k, v in c.items()}

    @staticmethod
    def _fatigue(r: _Round) -> float:
        if len(r.punch_ts) < 4 or r.start <= 0:
            return 1.0
        fc = r.start + FATIGUE_WINDOW_S
        lc = r.punch_ts[-1] - FATIGUE_WINDOW_S
        first = sum(1 for t in r.punch_ts if t <= fc)
        last = sum(1 for t in r.punch_ts if t >= lc)
        fr = first / FATIGUE_WINDOW_S if first else 0.001
        lr = last / FATIGUE_WINDOW_S if last else 0.0
        return round(lr / fr, 3) if fr > 0 else 1.0

    @staticmethod
    def _avg_fatigue(rounds: List[_Round]) -> float:
        vals = [AnalyticsNode._fatigue(r) for r in rounds if r.punch_ts]
        return round(sum(vals) / len(vals), 3) if vals else 1.0

    @staticmethod
    def _def_stats(evts: List[Dict]) -> Dict[str, Any]:
        if not evts:
            return {"rate": 0.0, "total": 0, "breakdown": {}}
        total = len(evts)
        ok = sum(1 for e in evts if not e["struck"])
        bd: Dict[str, int] = defaultdict(int)
        for e in evts:
            bd[e["type"]] += 1
        return {"rate": round(ok / total, 3), "total": total, "breakdown": dict(bd)}

    @staticmethod
    def _move_stats(dep: List[float], lat: List[float]) -> Dict[str, float]:
        ad = sum(dep) / len(dep) if dep else 0.0
        dr = (max(dep) - min(dep)) if len(dep) >= 2 else 0.0
        lt = sum(abs(v) for v in lat) if lat else 0.0
        return {"avg_depth": round(ad, 3), "depth_range": round(dr, 3), "lateral_displacement": round(lt, 1)}

    def _trends(self) -> Dict[str, Any]:
        if not self._history:
            return {"rolling_avg": {}, "personal_records": {}, "improvement": {}}
        w = self._history[-7:]
        ap = sum(h.get("total_punches", 0) for h in w) / len(w)
        am = sum(h.get("punches_per_minute", 0) for h in w) / len(w)
        ad = sum(h.get("defense", {}).get("rate", 0) for h in w) / len(w)
        hi_p = [h.get("total_punches", 0) for h in self._history]
        hi_m = [h.get("punches_per_minute", 0) for h in self._history]
        imp: Dict[str, float] = {}
        if len(self._history) >= 14:
            pm = sum(h.get("punches_per_minute", 0) for h in self._history[-14:-7]) / 7
            if pm > 0:
                imp["ppm_change_pct"] = round((am - pm) / pm * 100, 1)
        ra = {"punches": round(ap, 1), "punches_per_minute": round(am, 1), "defense_rate": round(ad, 3)}
        pr = {"max_punches": max(hi_p, default=0), "max_ppm": round(max(hi_m, default=0), 1)}
        return {"rolling_avg": ra, "personal_records": pr, "improvement": imp}

    # -- Publishing -------------------------------------------------------
    def _publish(self, data: Dict[str, Any]) -> None:
        msg = String()
        msg.data = json.dumps(data)
        self._pub.publish(msg)

    def _periodic(self) -> None:
        if self._sess is None or not self._active:
            return
        a = self._compute()
        a["partial"] = True
        self._publish(a)


def main(args: list[str] | None = None) -> None:
    """Entry point for the analytics node."""
    rclpy.init(args=args)
    node = AnalyticsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
