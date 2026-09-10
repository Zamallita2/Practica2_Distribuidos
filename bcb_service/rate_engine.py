"""
BCB (Banco Central de Bolivia) Exchange Rate Simulation Engine.
Fluctuates rate every 3 minutes (configurable) with ±0.9999 oscillation and 4 decimal precision.
"""

import time
import random
from config import BCB_BASE_EXCHANGE_RATE, BCB_UPDATE_INTERVAL_SECONDS, BCB_MAX_VARIATION

class BCBExchangeRateEngine:
    def __init__(self, base_rate: float = BCB_BASE_EXCHANGE_RATE, interval: int = BCB_UPDATE_INTERVAL_SECONDS):
        if interval <= 0:
            raise ValueError("El intervalo de actualización debe ser mayor que cero")
        self.base_rate = base_rate
        self.interval = interval
        self.start_time = time.time()
        self._last_period_index = -1
        self._last_rate = None

    def _calculate_rate(self, period_index: int) -> float:
        rng = random.Random(period_index + 42)
        variation = rng.uniform(-BCB_MAX_VARIATION, BCB_MAX_VARIATION)
        return round(self.base_rate + variation, 4)

    def get_current_rate(self) -> dict:
        now = time.time()
        elapsed = now - self.start_time
        period_index = int(elapsed // self.interval)

        if period_index != self._last_period_index:
            self._last_period_index = period_index
            self._last_rate = self._calculate_rate(period_index)

        current_rate = self._last_rate
        
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            "period_index": period_index,
            "base_rate": self.base_rate,
            "current_rate": current_rate,
            "seconds_until_next_change": int(self.interval - (elapsed % self.interval))
        }

    def reset(self) -> None:
        """Reinicia el ciclo del simulador, útil al iniciar una nueva simulación."""
        self.start_time = time.time()
        self._last_period_index = -1
        self._last_rate = None

# Global singleton instance
bcb_engine = BCBExchangeRateEngine()
