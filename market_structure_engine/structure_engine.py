from typing import List
from .models import Candle, MarketStructure, Trend
from .snr_detector import SNRDetector

class StructureEngine:
    """Основной движок: принимает свечи, строит структуру."""

    @staticmethod
    def detect_trend(candles: List[Candle], lookback: int = 20) -> Trend:
        """Простейший тренд: сравниваем цену закрытия последней свечи со свечой lookback баров назад."""
        if len(candles) < lookback + 1:
            return Trend.RANGE
        current = candles[-1].close
        past = candles[-lookback].close
        if current > past * 1.01:   # порог 1%
            return Trend.UP
        elif current < past * 0.99:
            return Trend.DOWN
        else:
            return Trend.RANGE

    @classmethod
    def analyze(cls, symbol: str, timeframe: str, candles: List[Candle]) -> MarketStructure:
        supports, resistances = SNRDetector.detect_supports_resistances(candles)
        trend = cls.detect_trend(candles)
        return MarketStructure(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            supports=supports,
            resistances=resistances,
            trend=trend
        )