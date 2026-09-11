"""
Lectura ligera de uso de CPU por núcleo (sin dependencias externas).
Usa /proc/stat en Linux; si no está disponible, reporta un único núcleo estimado.
"""

import os
import time
import threading
from collections import deque


def _read_proc_stat_cores():
    cores = []
    with open("/proc/stat", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("cpu") and len(line) > 3 and line[3].isdigit():
                parts = line.split()
                # user nice system idle iowait irq softirq steal
                nums = [int(x) for x in parts[1:9]]
                while len(nums) < 8:
                    nums.append(0)
                idle = nums[3] + nums[4]
                total = sum(nums)
                cores.append((idle, total))
    return cores


class CpuMonitor:
    def __init__(self, history_len: int = 40):
        self._lock = threading.Lock()
        self._prev = None
        self._history = deque(maxlen=history_len)
        self._core_count = os.cpu_count() or 1
        self.sample()  # baseline

    def sample(self):
        try:
            curr = _read_proc_stat_cores()
        except Exception:
            # Fallback sin /proc/stat
            load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
            pct = max(0.0, min(100.0, (load / self._core_count) * 100.0))
            with self._lock:
                self._history.append({
                    "t": time.strftime("%H:%M:%S"),
                    "cores": [round(pct, 1)],
                    "avg": round(pct, 1),
                })
            return self.snapshot()

        usages = []
        with self._lock:
            if self._prev and len(self._prev) == len(curr):
                for (pi, pt), (ci, ct) in zip(self._prev, curr):
                    d_total = ct - pt
                    d_idle = ci - pi
                    if d_total <= 0:
                        usages.append(0.0)
                    else:
                        usages.append(round(max(0.0, min(100.0, (1.0 - d_idle / d_total) * 100.0)), 1))
            else:
                usages = [0.0] * len(curr)
            self._prev = curr
            avg = round(sum(usages) / len(usages), 1) if usages else 0.0
            self._history.append({
                "t": time.strftime("%H:%M:%S"),
                "cores": usages,
                "avg": avg,
            })
            self._core_count = len(usages) or self._core_count

        return self.snapshot()

    def snapshot(self):
        with self._lock:
            latest = self._history[-1] if self._history else {"t": "--", "cores": [0.0], "avg": 0.0}
            return {
                "cpu_cores": self._core_count,
                "timestamp": latest["t"],
                "per_core_percent": latest["cores"],
                "average_percent": latest["avg"],
                "history": list(self._history),
                "loadavg": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
            }


cpu_monitor = CpuMonitor()
