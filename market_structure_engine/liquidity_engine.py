from typing import List, Tuple, Optional
from dataclasses import dataclass
from .models import MarketStructure, Candle

@dataclass
class LiquidityZone:
    level: float
    zone_low: float
    zone_high: float
    zone_type: str   # "above_swing_high", "below_swing_low", "above_resistance", "below_support"
    strength: float  # = atr * k

@dataclass
class LiquiditySweep:
    zone: LiquidityZone
    timestamp: int
    sweep_type: str   # "above" (пробой вверх с возвратом) или "below" (пробой вниз с возвратом)
    price_extreme: float  # максимальная (для above) или минимальная (для below) цена при свипе

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
        atr = sum(tr_values[-period:]) / period
        return atr

    @classmethod
    def build_liquidity_zones(cls, structure: MarketStructure, atr: float, k: float = 0.2) -> List[LiquidityZone]:
        zones = []
        # Зоны над свинг-хаями
        for sh in structure.swings_high:
            zone_low = sh
            zone_high = sh + atr * k
            zones.append(LiquidityZone(level=sh, zone_low=zone_low, zone_high=zone_high,
                                       zone_type="above_swing_high", strength=atr * k))
        # Зоны под свинг-лоями
        for sl in structure.swings_low:
            zone_low = sl - atr * k
            zone_high = sl
            zones.append(LiquidityZone(level=sl, zone_low=zone_low, zone_high=zone_high,
                                       zone_type="below_swing_low", strength=atr * k))
        # Зоны над сопротивлениями (уровнями)
        for r in structure.resistances:
            zone_low = r
            zone_high = r + atr * k
            zones.append(LiquidityZone(level=r, zone_low=zone_low, zone_high=zone_high,
                                       zone_type="above_resistance", strength=atr * k))
        # Зоны под поддержками
        for s in structure.supports:
            zone_low = s - atr * k
            zone_high = s
            zones.append(LiquidityZone(level=s, zone_low=zone_low, zone_high=zone_high,
                                       zone_type="below_support", strength=atr * k))
        return zones

    @classmethod
    def detect_sweeps(cls, candles: List[Candle], zones: List[LiquidityZone], lookback: int = 5) -> List[LiquiditySweep]:
        sweeps = []
        if len(candles) < 2:
            return sweeps
        start_idx = max(0, len(candles) - lookback)
        for zone in zones:
            for i in range(start_idx, len(candles)):
                candle = candles[i]
                if zone.zone_type in ("above_swing_high", "above_resistance"):
                    # Свип вверх: цена зашла выше zone_high, но закрылась ниже zone_high
                    if candle.high > zone.zone_high and candle.close < zone.zone_high:
                        sweeps.append(LiquiditySweep(
                            zone=zone,
                            timestamp=candle.timestamp,
                            sweep_type="above",
                            price_extreme=candle.high
                        ))
                elif zone.zone_type in ("below_swing_low", "below_support"):
                    # Свип вниз: цена ушла ниже zone_low, закрылась выше zone_low
                    if candle.low < zone.zone_low and candle.close > zone.zone_low:
                        sweeps.append(LiquiditySweep(
                            zone=zone,
                            timestamp=candle.timestamp,
                            sweep_type="below",
                            price_extreme=candle.low
                        ))
        return sweeps

    @classmethod
    def analyze(cls, structure: MarketStructure, atr_period: int = 14, k: float = 0.2, lookback: int = 5):
        candles = structure.candles
        atr = cls.calculate_atr(candles, atr_period)
        zones = cls.build_liquidity_zones(structure, atr, k)
        sweeps = cls.detect_sweeps(candles, zones, lookback)
        return {
            "zones": zones,
            "sweeps": sweeps,
            "atr": atr
        }