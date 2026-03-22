from collections import Counter
from database import Database

class Analyzer:
    def __init__(self):
        self.db = Database()

    def most_mentioned_assets(self, limit=10):
        ideas = self.db.get_all_ideas()
        assets = [idea['asset'] for idea in ideas if idea['asset']]
        return Counter(assets).most_common(limit)

    def direction_bias(self):
        ideas = self.db.get_all_ideas()
        directions = [idea['direction'] for idea in ideas if idea['direction']]
        long_count = directions.count('long')
        short_count = directions.count('short')
        total = long_count + short_count
        if total == 0:
            return {'long': 0, 'short': 0}
        return {
            'long': round(100 * long_count / total, 1),
            'short': round(100 * short_count / total, 1)
        }

    def average_level_by_asset(self, asset):
        ideas = self.db.get_all_ideas()
        levels = [idea['level'] for idea in ideas if idea['asset'] == asset and idea['level']]
        if not levels:
            return None
        return sum(levels) / len(levels)

    def print_report(self):
        print("=== Анализ Telegram-идей ===")
        print("\nСамые упоминаемые активы:")
        for asset, count in self.most_mentioned_assets(10):
            print(f"  {asset}: {count}")

        bias = self.direction_bias()
        print(f"\nСоотношение long/short: long {bias['long']}% / short {bias['short']}%")

if __name__ == '__main__':
    analyzer = Analyzer()
    analyzer.print_report()
