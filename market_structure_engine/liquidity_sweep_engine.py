from typing import List, Dict, Any
from dataclasses import dataclass
from .models import MarketStructure, Candle

@dataclass
class LiquiditySweepEvent:
    type: str          # "above" или "below"
    level: float       # уровень ликвидности, который был пробит
    source: str        # "equal_high", "equal_low", "liquidity_cluster", "resistance", "support"
    bars_ago: int      # сколько свечей назад произошёл sweep
    strength: float    # условная сила (пока 1.0, потом можно уточнить)

class LiquiditySweepEngine:
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
    def detect_sweeps(cls, candles: List[Candle], liquidity_zones: List[Any], lookback: int = 20) -> List[LiquiditySweepEvent]:
        """
        Обнаруживает sweep ликвидности на основе предоставленных зон (из LiquidityMapEngine).
        Каждая зона должна иметь атрибуты: zone_type, zone_low, zone_high, price_low, price_high.
        Для простоты мы принимаем словарь с ключами 'type', 'level_low', 'level_high'.
        """
        sweeps = []
        if len(candles) < 2:
            return sweeps

        start_idx = max(0, len(candles) - lookback)
        for zone in liquidity_zones:
            # Определяем уровень
            if zone.zone_type in ("equal_high", "above_resistance", "above_swing_high"):
                liquidity_level = zone.zone_high
                # Ищем самый свежий sweep: идём от конца к началу
                for i in range(len(candles)-1, start_idx-1, -1):
                    candle = candles[i]
                    if candle.high > liquidity_level and candle.close < liquidity_level:
                        bars_ago = len(candles) - i
                        sweeps.append(LiquiditySweepEvent(
                            type="above",
                            level=liquidity_level,
                            source=zone.zone_type,
                            bars_ago=bars_ago,
                            strength=1.0
                        ))
                        break  # нашли самый свежий для этой зоны
            elif zone.zone_type in ("equal_low", "below_support", "below_swing_low"):
                liquidity_level = zone.zone_low
                for i in range(len(candles)-1, start_idx-1, -1):
                    candle = candles[i]
                    if candle.low < liquidity_level and candle.close > liquidity_level:
                        bars_ago = len(candles) - i
                        sweeps.append(LiquiditySweepEvent(
                            type="below",
                            level=liquidity_level,
                            source=zone.zone_type,
                            bars_ago=bars_ago,
                            strength=1.0
                        ))
                        break

        # Дедупликация (оставляем самый свежий для каждого уровня)
        unique = {}
        for s in sweeps:
            key = (s.type, s.level)
            if key not in unique or s.bars_ago < unique[key].bars_ago:
                unique[key] = s
        return list(unique.values())

    @classmethod
    def analyze(cls, structure: MarketStructure, liquidity_zones: List[Any], lookback: int = 50) -> dict:
        candles = structure.candles
        sweeps = cls.detect_sweeps(candles, liquidity_zones, lookback)
        return {"sweeps": sweeps}