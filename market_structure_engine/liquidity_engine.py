from typing import List, Dict
from dataclasses import dataclass
from .models import MarketStructure, Candle

@dataclass
class LiquidityZone:
    zone_low: float
    zone_high: float
    zone_type: str
    touches: int
    strength: float
    distance: float

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

    @staticmethod
    def _is_swing_high(candles: List[Candle], i: int, left: int = 2, right: int = 2) -> bool:
        if i - left < 0 or i + right >= len(candles):
            return False
        current = candles[i].high
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if candles[j].high >= current:
                return False
        return True

    @staticmethod
    def _is_swing_low(candles: List[Candle], i: int, left: int = 2, right: int = 2) -> bool:
        if i - left < 0 or i + right >= len(candles):
            return False
        current = candles[i].low
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if candles[j].low <= current:
                return False
        return True

    @classmethod
    def detect_swings(cls, candles: List[Candle]) -> tuple:
        highs = []
        lows = []
        for i in range(len(candles)):
            if cls._is_swing_high(candles, i):
                highs.append(candles[i].high)
            if cls._is_swing_low(candles, i):
                lows.append(candles[i].low)
        return highs, lows

    @classmethod
    def cluster_swings(cls, swings: List[float], atr: float, cluster_threshold: float = 0.2) -> List[Dict]:
        if not swings:
            return []
        swings_sorted = sorted(swings)
        clusters = []
        current = [swings_sorted[0]]
        for s in swings_sorted[1:]:
            if (s - current[-1]) <= cluster_threshold * atr:
                current.append(s)
            else:
                clusters.append({
                    "low": min(current),
                    "high": max(current),
                    "touches": len(current)
                })
                current = [s]
        clusters.append({
            "low": min(current),
            "high": max(current),
            "touches": len(current)
        })
        return clusters

    @classmethod
    def build_zones(cls, high_clusters: List[Dict], low_clusters: List[Dict],
                    current_price: float, atr: float) -> List[LiquidityZone]:
        zones = []
        for cl in high_clusters:
            zone_type = "equal_high" if cl["touches"] >= 2 else "swing_high"
            mid = (cl["low"] + cl["high"]) / 2
            zones.append(LiquidityZone(
                zone_low=cl["low"],
                zone_high=cl["high"],
                zone_type=zone_type,
                touches=cl["touches"],
                strength=min(1.0, cl["touches"] / 6.0),
                distance=abs(current_price - mid)
            ))
        for cl in low_clusters:
            zone_type = "equal_low" if cl["touches"] >= 2 else "swing_low"
            mid = (cl["low"] + cl["high"]) / 2
            zones.append(LiquidityZone(
                zone_low=cl["low"],
                zone_high=cl["high"],
                zone_type=zone_type,
                touches=cl["touches"],
                strength=min(1.0, cl["touches"] / 6.0),
                distance=abs(current_price - mid)
            ))
        return zones

    @classmethod
    def analyze(cls, structure: MarketStructure, current_price: float,
                lookback: int = 150, cluster_threshold: float = 0.2,
                distance_limit: float = 3.0) -> Dict:
        candles = structure.candles[-lookback:]
        atr = cls.calculate_atr(candles, 14)
        swings_high, swings_low = cls.detect_swings(candles)
        high_clusters = cls.cluster_swings(swings_high, atr, cluster_threshold)
        low_clusters = cls.cluster_swings(swings_low, atr, cluster_threshold)
        all_zones = cls.build_zones(high_clusters, low_clusters, current_price, atr)
        filtered = [z for z in all_zones if z.distance <= distance_limit * atr]
        return {"zones": filtered, "atr": atr}