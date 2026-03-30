import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_structure_engine import DataFetcher, StructureEngine

def main():
    fetcher = DataFetcher()
    symbol = 'BTC/USDT'
    timeframe = '1h'
    candles = fetcher.fetch_ohlcv(symbol, timeframe, limit=200)
    structure = StructureEngine.analyze(symbol, timeframe, candles)

    print(f"Анализ {symbol} ({timeframe}):")
    print(f"Тренд: {structure.trend.value}")
    print(f"Поддержки: {', '.join(str(round(l,2)) for l in structure.supports[:5])}")
    print(f"Сопротивления: {', '.join(str(round(l,2)) for l in structure.resistances[:5])}")

if __name__ == '__main__':
    main()