from typing import List, Tuple
import numpy as np
from .models import Candle

class SNRDetector:
    """
    Обнаружение уровней поддержки/сопротивления через swing highs/lows.
    """

    @staticmethod
    def _is_swing_high(candles: List[Candle], i: int, left: int = 2, right: int = 2) -> bool:
        """Проверяет, является ли свеча i локальным максимумом."""
        if i - left < 0 or i + right >= len(candles):
            return False
        current_high = candles[i].high
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if candles[j].high >= current_high:
                return False
        return True

    @staticmethod
    def _is_swing_low(candles: List[Candle], i: int, left: int = 2, right: int = 2) -> bool:
        """Проверяет, является ли свеча i локальным минимумом."""
        if i - left < 0 or i + right >= len(candles):
            return False
        current_low = candles[i].low
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if candles[j].low <= current_low:
                return False
        return True

    @staticmethod
    def _cluster_levels(levels: List[float], tolerance: float = 0.001) -> List[float]:
        """
        Кластеризует близкие уровни. tolerance – относительное отклонение (0.001 = 0.1%).
        """
        if not levels:
            return []
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        for lvl in levels[1:]:
            if abs(lvl - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(lvl)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [lvl]
        clusters.append(np.mean(current_cluster))
        return clusters

    @classmethod
    def detect_supports_resistances(cls, candles: List[Candle],
                                    swing_window: int = 2,
                                    cluster_tolerance: float = 0.001) -> Tuple[List[float], List[float]]:
        """
        Возвращает (supports, resistances).
        """
        highs = []
        lows = []
        for i in range(len(candles)):
            if cls._is_swing_high(candles, i, left=swing_window, right=swing_window):
                highs.append(candles[i].high)
            if cls._is_swing_low(candles, i, left=swing_window, right=swing_window):
                lows.append(candles[i].low)

        resistances = cls._cluster_levels(highs, tolerance=cluster_tolerance)
        supports = cls._cluster_levels(lows, tolerance=cluster_tolerance)
        return supports, resistances