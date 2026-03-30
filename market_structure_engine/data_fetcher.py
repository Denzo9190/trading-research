import ccxt
from typing import List
from .models import Candle

class DataFetcher:
    def __init__(self, exchange_id='bingx', exchange_options=None):
        default_options = {
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}   # бессрочные фьючерсы
        }
        if exchange_options:
            default_options.update(exchange_options)
        self.exchange = getattr(ccxt, exchange_id)(default_options)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Candle]:
        """
        timeframe: '1m', '5m', '15m', '1h', '4h', '1d' и т.д.
        """
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        candles = []
        for o in ohlcv:
            candles.append(Candle(
                timestamp=o[0],
                open=o[1],
                high=o[2],
                low=o[3],
                close=o[4],
                volume=o[5]
            ))
        return candles