from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class Trend(Enum):
    UP = "UP"
    DOWN = "DOWN"
    RANGE = "RANGE"

@dataclass
class Candle:
    timestamp: int   # unix time in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class MarketStructure:
    symbol: str
    timeframe: str
    candles: List[Candle]
    supports: List[float]       # уровни поддержки
    resistances: List[float]    # уровни сопротивления
    trend: Trend
    last_breakout_level: Optional[float] = None

    def get_near_levels(self, current_price: float, tolerance: float = 0.02):
        """
        Возвращает (поддержки ниже цены, сопротивления выше цены)
        в пределах tolerance (2% по умолчанию) от current_price.
        """
        supports_below = [s for s in self.supports if s < current_price and abs(s - current_price)/current_price <= tolerance]
        resistances_above = [r for r in self.resistances if r > current_price and abs(r - current_price)/current_price <= tolerance]
        supports_below.sort(reverse=True)
        resistances_above.sort()
        return supports_below, resistances_above