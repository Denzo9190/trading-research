from typing import List
from dataclasses import dataclass
from .models import Candle, MarketStructure

@dataclass
class FVG:
    type: str
    price_low: float
    price_high: float
    size: float
    status: str        # "открыт", "тестирован", "проторгован", "прошит" (пока не используется в выводе)
    age: int

class ImbalanceEngine:
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

    # TODO: Статусы (открыт, тестирован, проторгован, прошит) реализованы в коде,
    #       но логика определения требует доработки (пока выдаёт некорректные результаты).
    #       В текущей версии статусы не выводятся в Telegram, чтобы не вводить в заблуждение.
    #       Будет исправлено в следующей итерации Imbalance Engine v0.2.
    @classmethod
    def _cluster_zones(cls, zones):
        if not zones:
            return []
        zones.sort(key=lambda x: x[1])
        merged = []
        cur = zones[0]
        for nxt in zones[1:]:
            if nxt[1] <= cur[2]:
                cur_low = min(cur[1], nxt[1])
                cur_high = max(cur[2], nxt[2])
                # статус с приоритетом: прошит > проторгован > тестирован > открыт
                statuses = [cur[3], nxt[3]]
                if "прошит" in statuses:
                    cur_status = "прошит"
                elif "заполнен" in statuses:
                    cur_status = "заполнен"
                elif "тестирован" in statuses:
                    cur_status = "тестирован"
                else:
                    cur_status = "открыт"
                cur_age = min(cur[4], nxt[4])
                cur = (cur[0], cur_low, cur_high, cur_status, cur_age)
            else:
                merged.append(cur)
                cur = nxt
        merged.append(cur)
        return merged

    @classmethod
    def detect_fvg(cls, candles: List[Candle], atr: float,
                   min_size_atr: float = 0.35,
                   max_distance_atr: float = 2.5) -> List[FVG]:
        raw_bullish = []
        raw_bearish = []
        if len(candles) < 3:
            return []
        current_price = candles[-1].close
        for i in range(len(candles)-2):
            c1 = candles[i]
            c2 = candles[i+1]
            c3 = candles[i+2]

            # Bullish FVG
            if c3.low > c1.high:
                price_low = c1.high
                price_high = c3.low
                size = price_high - price_low
                if size < min_size_atr * atr:
                    continue
                status = "открыт"
                for j in range(i+3, len(candles)):
                    candle = candles[j]
                    # Импульсный прошив (одна свеча перекрывает всю зону и импульсная)
                    if candle.low < price_low and candle.high > price_high:
                        if (candle.high - candle.low) > 1.5 * atr:
                            status = "прошит"
                            break
                        else:
                            status = "заполнен"
                    if status != "прошит" and candle.close > price_high:
                        status = "заполнен"
                    if status == "открыт" and (candle.high > price_low and candle.low < price_high):
                        status = "тестирован"
                age = len(candles) - (i+2)
                mid = (price_low + price_high) / 2
                distance = abs(current_price - mid)
                if distance > max_distance_atr * atr:
                    continue
                raw_bullish.append(("bullish", price_low, price_high, status, age))
            # Bearish FVG
            elif c3.high < c1.low:
                price_low = c3.high
                price_high = c1.low
                size = price_high - price_low
                if size < min_size_atr * atr:
                    continue
                status = "открыт"
                for j in range(i+3, len(candles)):
                    candle = candles[j]
                    if candle.low < price_low and candle.high > price_high:
                        if (candle.high - candle.low) > 1.5 * atr:
                            status = "прошит"
                            break
                        else:
                            status = "заполнен"
                    if status != "прошит" and candle.close < price_low:
                        status = "заполнен"
                    if status == "открыт" and (candle.high > price_low and candle.low < price_high):
                        status = "тестирован"
                age = len(candles) - (i+2)
                mid = (price_low + price_high) / 2
                distance = abs(current_price - mid)
                if distance > max_distance_atr * atr:
                    continue
                raw_bearish.append(("bearish", price_low, price_high, status, age))

        bullish_clusters = cls._cluster_zones(raw_bullish)
        bearish_clusters = cls._cluster_zones(raw_bearish)

        fvgs = []
        for typ, low, high, status, age in bullish_clusters:
            fvgs.append(FVG(type="bullish", price_low=low, price_high=high,
                            size=high-low, status=status, age=age))
        for typ, low, high, status, age in bearish_clusters:
            fvgs.append(FVG(type="bearish", price_low=low, price_high=high,
                            size=high-low, status=status, age=age))

        fvgs.sort(key=lambda x: abs(((x.price_low + x.price_high)/2) - current_price))
        return fvgs

    @classmethod
    def analyze(cls, structure: MarketStructure,
                min_size_atr: float = 0.35,
                max_distance_atr: float = 2.5) -> dict:
        candles = structure.candles
        atr = cls.calculate_atr(candles, 14)
        fvgs = cls.detect_fvg(candles, atr, min_size_atr, max_distance_atr)
        return {"fvgs": fvgs, "atr": atr}