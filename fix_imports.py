import os
import sys

# Добавляем текущую папку в путь
sys.path.insert(0, os.getcwd())

# Проверяем, видит ли Python market_structure_engine
try:
    import market_structure_engine
    print("✅ market_structure_engine найден")
except ImportError:
    print("❌ market_structure_engine НЕ найден")
    print("Текущая директория:", os.getcwd())
    print("Содержимое:", os.listdir())
    sys.exit(1)

# Проверяем импорт LiquidityMapEngine
try:
    from market_structure_engine.liquidity_engine import LiquidityMapEngine
    print("✅ LiquidityMapEngine импортирован")
except ImportError as e:
    print("❌ Ошибка импорта LiquidityMapEngine:", e)

# Проверяем tv_alert_handler
handler_path = "telegram_intelligence/tv_alert_relay/tv_alert_handler.py"
if os.path.exists(handler_path):
    print(f"✅ Файл {handler_path} существует")
else:
    print(f"❌ Файл {handler_path} не найден")