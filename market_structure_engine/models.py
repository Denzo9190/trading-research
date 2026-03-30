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