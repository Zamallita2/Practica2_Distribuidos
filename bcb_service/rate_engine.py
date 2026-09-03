"""
BCB (Banco Central de Bolivia) Exchange Rate Simulation Engine.
Fluctuates rate every 3 minutes (configurable) with ±0.9999 oscillation and 4 decimal precision.
"""

import time
import random
import math
from config import BCB_BASE_EXCHANGE_RATE, BCB_UPDATE_INTERVAL_SECONDS, BCB_MAX_VARIATION

class BCBExchangeRateEngine:
    def __init__(self, base_rate: float = BCB_BASE_EXCHANGE_RATE, interval: int = BCB_UPDATE_INTERVAL_SECONDS):
        self.base_rate = base_rate
        self.interval = interval
        self.start_time = time.time()

    def get_current_rate(self) -> dict:
        now = time.time()
        elapsed = now - self.start_time
        period_index = int(elapsed // self.interval)
        
        # Deterministic pseudo-random variation based on period index so concurrent calls get the exact same rate in the same window
        rng = random.Random(period_index + 42)
        variation = rng.uniform(-BCB_MAX_VARIATION, BCB_MAX_VARIATION)
        current_rate = round(self.base_rate + variation, 4)
        
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            "period_index": period_index,
            "base_rate": self.base_rate,
            "current_rate": current_rate,
            "seconds_until_next_change": int(self.interval - (elapsed % self.interval))
        }

# Global singleton instance
bcb_engine = BCBExchangeRateEngine()
