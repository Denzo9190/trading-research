import asyncio
from telethon import TelegramClient
from config import API_ID, API_HASH

async def main():
    client = TelegramClient('parser_session', API_ID, API_HASH)
    await client.start()

    # Открываем файл для записи
    with open('channels_raw.txt', 'w', encoding='utf-8') as f:
        # Заголовок для удобства (можно потом удалить вручную)
        f.write("ТИП\tНАЗВАНИЕ\tИДЕНТИФИКАТОР (для channels.json)\tВНУТРЕННИЙ ID\n")

        async for dialog in client.iter_dialogs():
            # Пропускаем личные чаты
            if not (dialog.is_channel or dialog.is_group):
                continue

            # Определяем тип
            if dialog.is_channel and dialog.is_group:
                entity_type = "супергруппа"
            elif dialog.is_channel:
                entity_type = "канал"
            elif dialog.is_group:
                entity_type = "группа"
            else:
                entity_type = "другое"

            username = getattr(dialog.entity, 'username', None)
            if username:
                identifier = f"t.me/{username}"
            else:
                identifier = f"{dialog.id}"  # просто число, но в JSON нужно будет в кавычках

            # Записываем строку с разделителями табуляции
            f.write(f"{entity_type}\t{dialog.name}\t{identifier}\t{dialog.id}\n")

    print("Список каналов и групп сохранён в файл channels_raw.txt")
    await client.disconnect()

asyncio.run(main())
