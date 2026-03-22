import sqlite3
from collections import Counter, defaultdict
import pandas as pd
from datetime import datetime, timezone
import json

class ChannelRanker:
    def __init__(self, db_path='tg_messages.db'):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_channel_stats(self):
        """
        Собирает расширенную статистику по каждому каналу.
        """
        # Статистика из messages
        cursor = self.conn.execute('''
            SELECT 
                channel,
                COUNT(*) as total_messages,
                MIN(date) as first_message_date,
                MAX(date) as last_message_date
            FROM messages
            GROUP BY channel
        ''')
        messages_stats = {row['channel']: dict(row) for row in cursor.fetchall()}

        # Статистика из ideas
        cursor = self.conn.execute('''
            SELECT 
                channel,
                COUNT(*) as total_ideas,
                COUNT(DISTINCT asset) as unique_assets
            FROM ideas
            GROUP BY channel
        ''')
        ideas_stats = {row['channel']: dict(row) for row in cursor.fetchall()}

        # Объединяем и вычисляем дополнительные метрики
        channels = []
        for channel, msg_stat in messages_stats.items():
            total_messages = msg_stat['total_messages']
            first_date = msg_stat['first_message_date']
            last_date = msg_stat['last_message_date']

            # Вычисляем возраст канала в днях
            if first_date:
                first = datetime.fromisoformat(first_date)
                last = datetime.fromisoformat(last_date)
                days_active = max(1, (last - first).days + 1)
                messages_per_day = total_messages / days_active
            else:
                messages_per_day = 0

            recency_days = (datetime.now(timezone.utc) - datetime.fromisoformat(last_date)).days if last_date else 999

            stats = {
                'channel': channel,
                'total_messages': total_messages,
                'first_message_date': first_date,
                'last_message_date': last_date,
                'messages_per_day': round(messages_per_day, 2),
                'recency_days': recency_days,
                'total_ideas': 0,
                'unique_assets': 0,
                'ideas_per_message': 0
            }

            if channel in ideas_stats:
                stats['total_ideas'] = ideas_stats[channel]['total_ideas']
                stats['unique_assets'] = ideas_stats[channel]['unique_assets']
                if total_messages > 0:
                    stats['ideas_per_message'] = stats['total_ideas'] / total_messages

            channels.append(stats)

        return channels

    def rank_channels(self):
        """
        Вычисляет рейтинг канала на основе:
        - количество идей (нормированное)
        - плотность идей (ideas_per_message)
        - разнообразие активов
        - активность (messages_per_day)
        - свежесть (чем меньше дней с последнего сообщения, тем лучше)
        """
        channels = self.get_channel_stats()

        # Нормализующие коэффициенты
        max_ideas = max((c['total_ideas'] for c in channels), default=1)
        max_ipm = max((c['ideas_per_message'] for c in channels), default=0.01)
        max_assets = max((c['unique_assets'] for c in channels), default=1)
        max_activity = max((c['messages_per_day'] for c in channels), default=1)
        max_recency_days = max((c['recency_days'] for c in channels), default=1)

        for c in channels:
            # Нормализация от 0 до 1 (чем больше, тем лучше)
            ideas_norm = c['total_ideas'] / max_ideas if max_ideas > 0 else 0
            ipm_norm = c['ideas_per_message'] / max_ipm if max_ipm > 0 else 0
            assets_norm = c['unique_assets'] / max_assets if max_assets > 0 else 0
            activity_norm = c['messages_per_day'] / max_activity if max_activity > 0 else 0
            # Для свежести: чем меньше recency_days, тем лучше. Используем обратную величину.
            recency_norm = 1 - (c['recency_days'] / max_recency_days) if max_recency_days > 0 else 0

            # Взвешенная сумма (веса можно менять)
            c['rank_score'] = (
                0.3 * ideas_norm +
                0.2 * ipm_norm +
                0.1 * assets_norm +
                0.2 * activity_norm +
                0.2 * recency_norm
            )

        # Сортируем по убыванию
        channels.sort(key=lambda x: x['rank_score'], reverse=True)
        return channels

    def export_to_csv(self, channels, filename='channel_ranking.csv'):
        df = pd.DataFrame(channels)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Экспортировано в {filename}")

    def suggest_channels_to_remove(self, channels, threshold_percent=30):
        """
        Предлагает каналы для удаления (нижние X% рейтинга).
        """
        total = len(channels)
        remove_count = int(total * threshold_percent / 100)
        to_remove = channels[-remove_count:]
        return to_remove

    def close(self):
        self.conn.close()

def main():
    ranker = ChannelRanker()
    channels = ranker.rank_channels()

    print(f"Всего каналов: {len(channels)}")
    print("\nТоп-10 каналов по рейтингу:")
    for i, ch in enumerate(channels[:10], 1):
        print(f"{i}. {ch['channel']} — идей: {ch['total_ideas']}, сообщ/день: {ch['messages_per_day']}, рейтинг: {ch['rank_score']:.3f}")

    # Предлагаем удалить нижние 30%
    to_remove = ranker.suggest_channels_to_remove(channels, threshold_percent=30)
    print(f"\nПредлагается удалить {len(to_remove)} каналов (нижние 30%):")
    for ch in to_remove[:10]:  # покажем первые 10 из удаляемых
        print(f"  {ch['channel']} (рейтинг: {ch['rank_score']:.3f})")

    # Экспорт в CSV для детального анализа
    ranker.export_to_csv(channels)
    ranker.close()

if __name__ == '__main__':
    main()
