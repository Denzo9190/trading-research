import os
import ccxt
from typing import List
from dotenv import load_dotenv
from .models import Candle

load_dotenv()

class DataFetcher:
    def __init__(self, exchange_id=None, market_type=None):
        self.exchange_id = exchange_id or os.getenv('EXCHANGE_ID', 'bingx')
        self.market_type = market_type or os.getenv('MARKET_TYPE', 'swap')

        exchange_class = getattr(ccxt, self.exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            'options': {
                'defaultType': self.market_type
            }
        })

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> List[Candle]:
        # Для BingX swap преобразуем BTC/USDT -> BTC/USDT:USDT
        if self.exchange_id == 'bingx' and self.market_type == 'swap':
            if not symbol.endswith(':USDT'):
                symbol = f"{symbol}:USDT"

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