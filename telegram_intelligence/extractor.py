import re
from database import Database

class IdeaExtractor:
    """
    Извлекает торговые идеи из текста сообщений.
    Поддерживает русские названия активов и разные формулировки.
    """
    def __init__(self):
        self.db = Database()
        # Словарь соответствий: ключевое слово -> стандартный тикер
        self.asset_map = {
            # BTC
            'btc': 'BTC', 'bitcoin': 'BTC', 'биткоин': 'BTC', 'биток': 'BTC',
            # ETH
            'eth': 'ETH', 'ethereum': 'ETH', 'эфир': 'ETH', 'эфириум': 'ETH',
            # SOL
            'sol': 'SOL', 'solana': 'SOL', 'солана': 'SOL',
            # BNB
            'bnb': 'BNB', 'binance coin': 'BNB',
            # ADA
            'ada': 'ADA', 'cardano': 'ADA', 'кардано': 'ADA',
            # XRP
            'xrp': 'XRP', 'рипл': 'XRP', 'ripple': 'XRP',
            # DOT
            'dot': 'DOT', 'polkadot': 'DOT', 'полкадот': 'DOT',
            # LINK
            'link': 'LINK', 'chainlink': 'LINK',
            # MATIC
            'matic': 'MATIC', 'polygon': 'MATIC',
            # AVAX
            'avax': 'AVAX', 'avalanche': 'AVAX',
            # DOGE
            'doge': 'DOGE', 'dogecoin': 'DOGE', 'доги': 'DOGE',
            # SHIB
            'shib': 'SHIB', 'shiba': 'SHIB',
            # UNI
            'uni': 'UNI', 'uniswap': 'UNI',
        }

        # Регулярка для поиска чисел (цены)
        self.price_re = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?|\b\d+\.?\d*\b')

        # Направления: ключевые слова и соответствующий direction
        self.direction_map = {
            # английские
            'long': 'long', 'buy': 'long', 'bought': 'long',
            'short': 'short', 'sell': 'short', 'sold': 'short',
            # русские
            'в лонг': 'long', 'лонг': 'long', 'покупка': 'long', 'покупаем': 'long', 'купить': 'long',
            'в шорт': 'short', 'шорт': 'short', 'продажа': 'short', 'продаем': 'short', 'продать': 'short',
            'выше': 'long', 'ниже': 'short',
            'бычий': 'long', 'медвежий': 'short',
        }

    def extract_ideas_from_message(self, date, channel, text):
        text_lower = text.lower()
        ideas = []

        # Ищем все упомянутые активы
        found_assets = set()
        for word, asset in self.asset_map.items():
            # Ищем слово как отдельное (с границами слова)
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                found_assets.add(asset)

        if not found_assets:
            return []  # нет активов – не идея

        # Ищем направление
        direction = None
        for phrase, dir_val in self.direction_map.items():
            if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
                direction = dir_val
                break

        # Ищем уровень цены (первое число)
        price_match = self.price_re.search(text)
        level = float(price_match.group().replace(',', '')) if price_match else None

        # Ищем цель (target)
        target = None
        target_patterns = [
            r'target\s+(\d+\.?\d*)',
            r'цель\s+(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*target',
            r'(\d+\.?\d*)\s*цель',
            r'тейк\s+(\d+\.?\d*)',
            r'take\s+(\d+\.?\d*)',
        ]
        for pattern in target_patterns:
            match = re.search(pattern, text_lower)
            if match:
                target = float(match.group(1).replace(',', ''))
                break

        # Для каждого найденного актива создаём идею (если есть направление или уровень)
        for asset in found_assets:
            # Если нет направления и нет уровня – пропускаем (слишком неопределённо)
            if direction or level:
                ideas.append({
                    'asset': asset,
                    'direction': direction,
                    'level': level,
                    'target': target
                })

        return ideas

    def process_all_unprocessed(self):
        messages = self.db.get_all_messages()
        idea_count = 0
        for msg in messages:
            date = msg['date']
            channel = msg['channel']
            text = msg['text']
            ideas = self.extract_ideas_from_message(date, channel, text)
            for idea in ideas:
                self.db.insert_idea(
                    date=date,
                    channel=channel,
                    asset=idea['asset'],
                    direction=idea['direction'],
                    level=idea['level'],
                    target=idea['target'],
                    text=text
                )
                idea_count += 1
        print(f"Обработано сообщений: {len(messages)}, извлечено идей: {idea_count}")

def main():
    extractor = IdeaExtractor()
    extractor.process_all_unprocessed()

if __name__ == '__main__':
    main()
