from typing import List
from dataclasses import dataclass
from .models import MarketStructure, Candle

@dataclass
class LiquidityZone:
    level: float
    zone_low: float
    zone_high: float
    zone_type: str  # "above_resistance" или "below_support"

@dataclass
class LiquiditySweep:
    zone: LiquidityZone
    timestamp: int
    sweep_type: str
    price_extreme: float
    depth: float  # глубина прокола в абсолютных единицах

class LiquidityMapEngine:
    @staticmethod
    def calculate_atr(candles: List[Candle], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.0
        tr_values = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i-1].close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        return sum(tr_values[-period:]) / period

    @classmethod
    def build_zones(cls,
                    resistance_levels: List[float],
                    support_levels: List[float],
                    atr: float,
                    percent: float = 0.0003,
                    atr_mult: float = 0.08) -> List[LiquidityZone]:
        zones = []
        # Зоны над сопротивлениями
        for r in resistance_levels:
            size = max(r * percent, atr * atr_mult)
            zones.append(LiquidityZone(
                level=r,
                zone_low=r,
                zone_high=r + size,
                zone_type="above_resistance"
            ))
        # Зоны под поддержками
        for s in support_levels:
            size = max(s * percent, atr * atr_mult)
            zones.append(LiquidityZone(
                level=s,
                zone_low=s - size,
                zone_high=s,
                zone_type="below_support"
            ))
        return zones

    @classmethod
    def detect_sweeps(cls, candles: List[Candle], zones: List[LiquidityZone], atr: float, lookback: int = 5, min_depth_ratio: float = 0.1) -> List[LiquiditySweep]:
        sweeps = []
        if len(candles) < 2:
            return sweeps
        start = max(0, len(candles) - lookback)
        for zone in zones:
            for candle in candles[start:]:
                if zone.zone_type == "above_resistance":
                    if candle.high > zone.zone_high:
                        depth = candle.high - zone.zone_high
                        if depth > min_depth_ratio * atr and candle.close < zone.zone_high:
                            sweeps.append(LiquiditySweep(
                                zone=zone, timestamp=candle.timestamp,
                                sweep_type="above", price_extreme=candle.high,
                                depth=depth
                            ))
                elif zone.zone_type == "below_support":
                    if candle.low < zone.zone_low:
                        depth = zone.zone_low - candle.low
                        if depth > min_depth_ratio * atr and candle.close > zone.zone_low:
                            sweeps.append(LiquiditySweep(
                                zone=zone, timestamp=candle.timestamp,
                                sweep_type="below", price_extreme=candle.low,
                                depth=depth
                            ))
        # Дедупликация: оставляем последний свип для каждой зоны
        sweeps_by_zone = {}
        for s in sweeps:
            key = (s.zone.zone_type, s.zone.level)
            if key not in sweeps_by_zone or s.timestamp > sweeps_by_zone[key].timestamp:
                sweeps_by_zone[key] = s
        return list(sweeps_by_zone.values())

    @classmethod
    def analyze(cls,
                structure: MarketStructure,
                resistance_levels: List[float],
                support_levels: List[float],
                percent: float = 0.0003,
                atr_mult: float = 0.08,
                lookback: int = 5,
                min_depth_ratio: float = 0.1):
        candles = structure.candles
        atr = cls.calculate_atr(candles, 14)
        zones = cls.build_zones(resistance_levels, support_levels, atr, percent, atr_mult)
        sweeps = cls.detect_sweeps(candles, zones, atr, lookback, min_depth_ratio)
        return {"zones": zones, "sweeps": sweeps, "atr": atr}