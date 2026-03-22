import asyncio
import json
import time
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import ImportChatInviteRequest
from database import Database
from config import API_ID, API_HASH

class TelegramParser:
    """
    Парсер сообщений из Telegram-каналов.
    Поддерживает:
    - публичные username (t.me/username или просто username)
    - внутренние числовые ID (например, "-1001234567890")
    - хеши пригласительных ссылок (abcXYZ123)
    """
    def __init__(self, channels_file='channels.json', session_name='parser_session'):
        self.channels_file = channels_file
        self.session_name = session_name
        self.db = Database()
        self.client = TelegramClient(session_name, API_ID, API_HASH)

    def load_channels(self):
        with open(self.channels_file, 'r', encoding='utf-8') as f:
            channels = json.load(f)
        return channels

    async def get_entity_by_id_or_link(self, channel_identifier):
        """
        Пытается получить entity канала по:
        - username или ссылке (через get_entity)
        - числовому ID (как строка, начинающаяся с '-')
        - хешу пригласительной ссылки (короткая строка без слешей)
        """
        # Сначала пробуем стандартный способ (username или ссылка)
        try:
            entity = await self.client.get_entity(channel_identifier)
            return entity
        except Exception:
            pass

        # Если это похоже на числовой ID (строка, начинающаяся с '-')
        if isinstance(channel_identifier, str) and channel_identifier.startswith('-'):
            try:
                # Преобразуем в int и пробуем получить entity по ID
                entity = await self.client.get_entity(int(channel_identifier))
                return entity
            except Exception:
                pass

        # Если это хеш пригласительной ссылки (короткая строка без слешей)
        if isinstance(channel_identifier, str) and '/' not in channel_identifier and len(channel_identifier) < 30:
            try:
                updates = await self.client(ImportChatInviteRequest(channel_identifier))
                # Возвращаем первый канал из обновлений
                return updates.chats[0]
            except Exception as e:
                print(f"Не удалось подключиться по приглашению {channel_identifier}: {e}")
                return None

        return None

    async def parse_channel(self, channel, limit=500):
        """
        Скачивает последние `limit` сообщений из одного канала.
        Возвращает количество новых сообщений.
        """
        entity = await self.get_entity_by_id_or_link(channel)
        if not entity:
            print(f"Не удалось получить доступ к каналу {channel}")
            return 0

        count = 0
        try:
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text and message.text.strip():
                    date_str = message.date.isoformat()
                    # В качестве имени канала сохраняем его название (для читаемости)
                    channel_name = getattr(entity, 'title', entity.username or str(channel))
                    self.db.insert_message(date_str, channel_name, message.text.strip())
                    count += 1
        except FloodWaitError as e:
            print(f"Flood wait: нужно подождать {e.seconds} секунд")
            time.sleep(e.seconds)
        except Exception as e:
            print(f"Ошибка при парсинге канала {channel}: {e}")
        return count

    async def run(self, limit_per_channel=500):
        await self.client.start()
        print("Клиент Telegram запущен.")

        channels = self.load_channels()
        total_messages = 0
        total_channels = len(channels)

        for idx, channel in enumerate(channels, 1):
            print(f"[{idx}/{total_channels}] Парсинг канала: {channel}")
            msgs = await self.parse_channel(channel, limit=limit_per_channel)
            total_messages += msgs
            print(f"  Добавлено сообщений: {msgs}")

        print(f"\nПарсинг завершён. Обработано каналов: {total_channels}, собрано сообщений: {total_messages}")
        await self.client.disconnect()

def main():
    parser = TelegramParser()
    asyncio.run(parser.run(limit_per_channel=500))

if __name__ == '__main__':
    main()
