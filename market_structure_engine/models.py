from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class Trend(Enum):
    UP = "UP"
    DOWN = "DOWN"
    RANGE = "RANGE"

@dataclass
class Candle:
    timestamp: int
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
    supports: List[float]
    resistances: List[float]
    trend: Trend
    swings_high: List[float] = None      # локальные максимумы
    swings_low: List[float] = None       # локальные минимумы