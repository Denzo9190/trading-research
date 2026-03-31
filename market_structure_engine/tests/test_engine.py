from market_structure_engine.data_fetcher import DataFetcher
from market_structure_engine.structure_engine import StructureEngine

fetcher = DataFetcher()
candles = fetcher.fetch_ohlcv('BTC/USDT', '1h', limit=200)
structure = StructureEngine.analyze('BTC/USDT', '1h', candles)
print(f"Тренд: {structure.trend.value}")
print(f"Поддержки: {[float(l) for l in structure.supports[:3]]}")
print(f"Сопротивления: {[float(r) for r in structure.resistances[:3]]}")