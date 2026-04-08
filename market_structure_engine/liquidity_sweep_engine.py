from typing import List
from dataclasses import dataclass
from .models import MarketStructure, Candle
from .liquidity_engine import LiquidityZone

@dataclass
class LiquiditySweepEvent:
    type: str          # "above" или "below"
    source: str        # "equal_high", "equal_low", "swing_high", "swing_low"
    level: float
    bars_ago: int
    # Данные свечи, на которой произошёл свип
    candle_high: float
    candle_low: float
    candle_close: float
    candle_open: float = None  # опционально

class LiquiditySweepEngine:
    @classmethod
    def detect_sweeps(cls, candles: List[Candle], zones: List[LiquidityZone], lookback: int = 20) -> List[LiquiditySweepEvent]:
        sweeps = []
        if len(candles) < 5:
            return sweeps

        current_price = candles[-1].close
        start_idx = max(0, len(candles) - lookback)

        # средний размер свечи для displacement фильтра
        ranges = [c.high - c.low for c in candles[-20:-1]]
        avg_range = sum(ranges) / len(ranges) if ranges else 0

        for zone in zones:
            if zone.zone_type in ("equal_high", "swing_high"):
                level = zone.zone_high
                sweep_type = "above"
            elif zone.zone_type in ("equal_low", "swing_low"):
                level = zone.zone_low
                sweep_type = "below"
            else:
                continue

            # фильтр: уровень слишком далеко от текущей цены (>5%)
            if abs(level - current_price) / current_price > 0.05:
                continue

            # проверяем только закрытые свечи (начиная с предпоследней)
            for i in range(len(candles) - 2, start_idx - 1, -1):
                candle = candles[i]

                if sweep_type == "above":
                    sweep_condition = (candle.high > level and candle.close < level)
                else:
                    sweep_condition = (candle.low < level and candle.close > level)

                if not sweep_condition:
                    continue

                # displacement фильтр: свеча должна быть не меньше среднего размера
                candle_range = candle.high - candle.low
                if avg_range > 0 and candle_range < avg_range * 1.2:
                    continue

                sweeps.append(LiquiditySweepEvent(
                    type=sweep_type,
                    source=zone.zone_type,
                    level=level,
                    bars_ago=len(candles) - 1 - i,
                    candle_high=candle.high,
                    candle_low=candle.low,
                    candle_close=candle.close,
                    candle_open=candle.open
                ))
                break  # берём только самый свежий свип для этой зоны

        # дедупликация: оставляем самый свежий свип для каждого (type, level)
        unique = {}
        for s in sweeps:
            key = (s.type, round(s.level, 2))
            if key not in unique or s.bars_ago < unique[key].bars_ago:
                unique[key] = s
        return list(unique.values())

    @classmethod
    def analyze(cls, structure: MarketStructure, zones: List[LiquidityZone], lookback: int = 20) -> dict:
        sweeps = cls.detect_sweeps(structure.candles, zones, lookback)
        return {"sweeps": sweeps}