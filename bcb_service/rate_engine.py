"""
BCB (Banco Central de Bolivia) Exchange Rate Simulation Engine.
La cotización fluctúa sola en un hilo daemon cada N segundos (±0.9999, 4 decimales).
ASFI lee siempre el valor vivo vía get_current_rate() / current_rate.
"""

import time
import random
import threading
from collections import deque
from config import BCB_BASE_EXCHANGE_RATE, BCB_UPDATE_INTERVAL_SECONDS, BCB_MAX_VARIATION


class BCBExchangeRateEngine:
    def __init__(
        self,
        base_rate: float = BCB_BASE_EXCHANGE_RATE,
        interval: int = BCB_UPDATE_INTERVAL_SECONDS,
        auto_start: bool = True,
    ):
        if interval <= 0:
            raise ValueError("El intervalo de actualización debe ser mayor que cero")
        self.base_rate = float(base_rate)
        self.interval = int(interval)
        self._lock = threading.RLock()
        self._last_rate = None
        self._previous_rate = None
        self._period_index = 0
        self._changed_at = time.time()
        self._history = deque(maxlen=60)
        self._stop = threading.Event()
        self._ticker = None

        self._apply_new_rate(force_different=False)
        if auto_start:
            self._start_ticker()

    def force_tick(self) -> float:
        """Fuerza una fluctuación inmediata (útil en pruebas y demos)."""
        with self._lock:
            self._period_index += 1
            return self._apply_new_rate(force_different=True)

    def stop(self) -> None:
        self._stop.set()
        t = self._ticker
        if t and t.is_alive():
            t.join(timeout=1.0)

    def _apply_new_rate(self, force_different: bool = True) -> float:
        """Genera y publica una nueva cotización (llamar con lock o desde __init__)."""
        variation = random.uniform(-BCB_MAX_VARIATION, BCB_MAX_VARIATION)
        new_rate = round(self.base_rate + variation, 4)
        if force_different and self._last_rate is not None:
            tries = 0
            while abs(new_rate - self._last_rate) < 0.05 and tries < 8:
                # Garantizar cambio VISIBLE (>= 0.05 BOB)
                variation = random.uniform(-BCB_MAX_VARIATION, BCB_MAX_VARIATION)
                new_rate = round(self.base_rate + variation, 4)
                tries += 1
            if abs(new_rate - self._last_rate) < 0.05:
                direction = 1 if self._last_rate <= self.base_rate else -1
                new_rate = round(min(self.base_rate + BCB_MAX_VARIATION,
                                     max(self.base_rate - BCB_MAX_VARIATION,
                                         self._last_rate + direction * 0.15)), 4)

        self._previous_rate = self._last_rate
        self._last_rate = new_rate
        self._changed_at = time.time()
        self._history.append({
            "t": time.strftime("%H:%M:%S"),
            "rate": new_rate,
            "period": self._period_index,
        })
        return new_rate

    def _ticker_loop(self):
        while not self._stop.is_set():
            # Esperar el intervalo actual (se puede acortar si cambia set_interval)
            wait_s = max(0.2, float(self.interval))
            if self._stop.wait(wait_s):
                break
            with self._lock:
                self._period_index += 1
                self._apply_new_rate(force_different=True)
                print(f"💱 [BCB] Nueva cotización: {self._last_rate:.4f} BOB/USD (periodo #{self._period_index})")

    def _start_ticker(self):
        if self._ticker and self._ticker.is_alive():
            return
        self._stop.clear()
        self._ticker = threading.Thread(target=self._ticker_loop, name="BCB-RateTicker", daemon=True)
        self._ticker.start()

    def get_current_rate(self) -> dict:
        with self._lock:
            now = time.time()
            elapsed_in_period = max(0.0, now - self._changed_at)
            seconds_until = max(0.0, self.interval - elapsed_in_period)
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
            self.interval = int(interval)
            # Nueva cotización inmediata al cambiar el intervalo (feedback visual)
            self._period_index += 1
            self._apply_new_rate(force_different=True)

    def reset(self) -> None:
        with self._lock:
            self._period_index = 0
            self._apply_new_rate(force_different=True)


# Global singleton — arranca el ticker al importar el módulo
bcb_engine = BCBExchangeRateEngine()
