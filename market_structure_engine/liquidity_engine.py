from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from .models import MarketStructure, Candle

class EventType(Enum):
    LIQUIDITY_POOL = "liquidity_pool"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    # позже: FVG, ORDER_BLOCK, STRUCTURE_BREAK, RANGE

@dataclass
class MarketEvent:
    event_type: EventType
    subtype: str           # "equal_high", "equal_low", "swing_high", "swing_low", "above_resistance", "below_support"
    price_low: float
    price_high: float
    strength: float        # 0..1
    timestamp: int         # время последнего касания или свечи
    tf: str                # таймфрейм
    metadata: Dict = None  # дополнительные поля (touch_count, cluster_width, sweep_depth и т.д.)

@dataclass
class LiquidityZone:
    level: float
    zone_low: float
    zone_high: float
    zone_type: str
    touch_count: int
    cluster_width: float
    age: int
    strength: float

@dataclass
class LiquiditySweep:
    zone: LiquidityZone
    timestamp: int
    sweep_type: str
    price_extreme: float

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
    def cluster_swings(cls, swings: List[float],
                       max_distance_pct: float = 0.0025,   # 0.25%
                       max_width_pct: float = 0.0035) -> List[Dict]:
        """
        Группирует близкие свинги в кластеры.
        Возвращает список кластеров с ключами: low, high, touches, last_idx.
        """
        if not swings:
            return []
        swings_sorted = sorted(swings)
        clusters = []
        current = [swings_sorted[0]]
        for s in swings_sorted[1:]:
            if (s - current[-1]) / current[-1] <= max_distance_pct:
                current.append(s)
            else:
                clusters.append(current)
                current = [s]
        clusters.append(current)

        # Вторичная кластеризация: разбиваем слишком широкие кластеры
        final = []
        for cluster in clusters:
            low = min(cluster)
            high = max(cluster)
            width_pct = (high - low) / low
            if width_pct <= max_width_pct:
                final.append({
                    "low": low,
                    "high": high,
                    "touches": len(cluster),
                    "last_idx": -1
                })
            else:
                # разбиваем на более мелкие части (жадным алгоритмом)
                sub = []
                sub_cluster = [cluster[0]]
                for val in cluster[1:]:
                    if (val - sub_cluster[-1]) / sub_cluster[-1] <= max_distance_pct:
                        sub_cluster.append(val)
                    else:
                        sub.append(sub_cluster)
                        sub_cluster = [val]
                sub.append(sub_cluster)
                for sc in sub:
                    final.append({
                        "low": min(sc),
                        "high": max(sc),
                        "touches": len(sc),
                        "last_idx": -1
                    })
        # Фильтр: отбрасываем кластеры с одним касанием (не кластер)
        final = [c for c in final if c["touches"] >= 2]
        return final

    @classmethod
    def detect_clusters(cls, structure: MarketStructure, lookback: int = 100,
                        max_distance_pct: float = 0.0025,
                        max_width_pct: float = 0.0035) -> Tuple[List[Dict], List[Dict]]:
        """
        Обнаруживает кластеры свингов за последние lookback свечей.
        Возвращает (high_clusters, low_clusters).
        """
        candles = structure.candles[-lookback:]
        # Пересчитываем свинги за этот период
        from .snr_detector import SNRDetector
        swings_high, swings_low = SNRDetector.detect_swings(candles, left=2, right=2)
        high_clusters = cls.cluster_swings(swings_high, max_distance_pct, max_width_pct)
        low_clusters = cls.cluster_swings(swings_low, max_distance_pct, max_width_pct)
        return high_clusters, low_clusters

    @classmethod
    def build_zones(cls, high_clusters: List[Dict], low_clusters: List[Dict],
                    current_price: float, atr: float) -> List[LiquidityZone]:
        """
        Преобразует кластеры в LiquidityZone.
        Для кластеров, расположенных выше цены – тип equal_high, ниже – equal_low.
        Одиночные свинги не включаются (только кластеры с touches>=2).
        """
        zones = []
        # Кластеры выше цены (equal high)
        for cl in high_clusters:
            low = cl["low"]
            high = cl["high"]
            touches = cl["touches"]
            # Не добавляем слишком широкие кластеры (дополнительная защита)
            if (high - low) / low > 0.0035:   # шире 0.35% – пропускаем
                continue
            zones.append(LiquidityZone(
                level=(low+high)/2,
                zone_low=low,
                zone_high=high,
                zone_type="equal_high",
                touch_count=touches,
                cluster_width=high-low,
                age=0,
                strength=touches / (1+0)   # временно
            ))
        # Кластеры ниже цены (equal low)
        for cl in low_clusters:
            low = cl["low"]
            high = cl["high"]
            touches = cl["touches"]
            if (high - low) / low > 0.0035:
                continue
            zones.append(LiquidityZone(
                level=(low+high)/2,
                zone_low=low,
                zone_high=high,
                zone_type="equal_low",
                touch_count=touches,
                cluster_width=high-low,
                age=0,
                strength=touches
            ))
        return zones

    @classmethod
    def detect_sweeps(cls, candles: List[Candle], zones: List[LiquidityZone], atr: float, lookback: int = 5) -> List[LiquiditySweep]:
        sweeps = []
        if len(candles) < 2:
            return sweeps
        start = max(0, len(candles) - lookback)
        for zone in zones:
            for i in range(start, len(candles)):
                candle = candles[i]
                if zone.zone_type == "equal_high":
                    if candle.high > zone.zone_high and candle.close < zone.zone_high:
                        depth = candle.high - zone.zone_high
                        if depth > 0.1 * atr:
                            sweeps.append(LiquiditySweep(
                                zone=zone, timestamp=candle.timestamp,
                                sweep_type="above", price_extreme=candle.high
                            ))
                elif zone.zone_type == "equal_low":
                    if candle.low < zone.zone_low and candle.close > zone.zone_low:
                        depth = zone.zone_low - candle.low
                        if depth > 0.1 * atr:
                            sweeps.append(LiquiditySweep(
                                zone=zone, timestamp=candle.timestamp,
                                sweep_type="below", price_extreme=candle.low
                            ))
        # Дедупликация: последний свип на зону
        latest = {}
        for s in sweeps:
            key = (s.zone.zone_type, s.zone.level)
            if key not in latest or s.timestamp > latest[key].timestamp:
                latest[key] = s
        return list(latest.values())

    @classmethod
    def analyze(cls, structure: MarketStructure,
                current_price: float,
                lookback: int = 100,
                max_distance_pct: float = 0.0025,
                max_width_pct: float = 0.0035,
                sweep_lookback: int = 5) -> Dict:
        """
        Возвращает словарь с ключами "zones", "sweeps", "atr".
        """
        candles = structure.candles
        atr = cls.calculate_atr(candles, 14)
        high_clusters, low_clusters = cls.detect_clusters(
            structure, lookback, max_distance_pct, max_width_pct
        )
        zones = cls.build_zones(high_clusters, low_clusters, current_price, atr)
        sweeps = cls.detect_sweeps(candles, zones, atr, sweep_lookback)
        return {"zones": zones, "sweeps": sweeps, "atr": atr}