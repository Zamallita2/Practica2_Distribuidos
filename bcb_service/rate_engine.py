"""
BCB (Banco Central de Bolivia) Exchange Rate Simulation Engine.
Fluctúa la cotización en un hilo de fondo cada N segundos (±0.9999, 4 decimales).
La ASFI lee siempre la cotización vigente vía get_current_rate().
"""

import time
import random
import threading
from collections import deque
from config import BCB_BASE_EXCHANGE_RATE, BCB_UPDATE_INTERVAL_SECONDS, BCB_MAX_VARIATION


class BCBExchangeRateEngine:
    def __init__(self, base_rate: float = BCB_BASE_EXCHANGE_RATE, interval: int = BCB_UPDATE_INTERVAL_SECONDS):
        if interval <= 0:
            raise ValueError("El intervalo de actualización debe ser mayor que cero")
        self.base_rate = base_rate
        self.interval = interval
        self._lock = threading.RLock()
        self._last_rate = None
        self._previous_rate = None
        self._period_index = 0
        self._next_change_at = time.time()
        self._history = deque(maxlen=60)
        self._stop = threading.Event()
        self._ticker = None
        self._roll_new_rate(reason="init")
        self._start_ticker()

    def _roll_new_rate(self, reason: str = "tick") -> float:
        variation = random.uniform(-BCB_MAX_VARIATION, BCB_MAX_VARIATION)
        new_rate = round(self.base_rate + variation, 4)
        if self._last_rate is not None and abs(new_rate - self._last_rate) < 0.05:
            # Forzar un salto visible (≥ 0.05) para que se note en el dashboard
            bump = 0.15 + random.uniform(0.05, 0.55)
            sign = -1 if (self._last_rate >= self.base_rate) else 1
            new_rate = round(min(self.base_rate + BCB_MAX_VARIATION,
                                 max(self.base_rate - BCB_MAX_VARIATION,
                                     self._last_rate + sign * bump)), 4)
        self._previous_rate = self._last_rate
        self._last_rate = new_rate
        self._period_index += 1 if reason != "init" else 0
        if reason == "init":
            self._period_index = 0
        self._next_change_at = time.time() + self.interval
        self._history.append({
            "t": time.strftime("%H:%M:%S"),
            "rate": new_rate,
            "period": self._period_index,
            "reason": reason,
        })
        return new_rate

    def _ticker_loop(self):
        while not self._stop.wait(0.25):
            with self._lock:
                if time.time() >= self._next_change_at:
                    self._roll_new_rate(reason="tick")

    def _start_ticker(self):
        if self._ticker and self._ticker.is_alive():
            return
        self._stop.clear()
        self._ticker = threading.Thread(target=self._ticker_loop, name="BCB-Ticker", daemon=True)
        self._ticker.start()

    def get_current_rate(self) -> dict:
        with self._lock:
            now = time.time()
            seconds_until = max(0.0, self._next_change_at - now)
            delta = None
            if self._previous_rate is not None:
                delta = round(self._last_rate - self._previous_rate, 4)
            return {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                "period_index": self._period_index,
                "base_rate": self.base_rate,
                "current_rate": self._last_rate,
                "previous_rate": self._previous_rate,
                "delta": delta,
                "interval": self.interval,
                "seconds_until_next_change": int(seconds_until),
                "fraction_until_next_change": round(seconds_until / self.interval, 4) if self.interval else 0,
                "history": list(self._history),
                "ticker_alive": bool(self._ticker and self._ticker.is_alive()),
            }

    def set_interval(self, interval: int) -> None:
        if interval <= 0:
            raise ValueError("El intervalo de actualización debe ser mayor que cero")
        with self._lock:
            self.interval = interval
            self._roll_new_rate(reason="interval_change")
        self._start_ticker()

    def reset(self) -> None:
        with self._lock:
            self._period_index = -1
            self._roll_new_rate(reason="reset")
        self._start_ticker()


# Global singleton instance
bcb_engine = BCBExchangeRateEngine()
