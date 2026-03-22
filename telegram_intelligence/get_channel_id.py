import asyncio
from telethon import TelegramClient
from config import API_ID, API_HASH

async def main():
    client = TelegramClient('parser_session', API_ID, API_HASH)
    await client.start()
    
    print("Каналы и группы (исключены личные чаты):")
    print("-" * 70)
    
    async for dialog in client.iter_dialogs():
        # Определяем тип диалога
        is_channel = dialog.is_channel
        is_group = dialog.is_group
        is_user = not (is_channel or is_group)  # личный чат или бот

        # Пропускаем личные чаты
        if is_user:
            continue

        # Определяем название типа для вывода
        if is_channel and is_group:
            entity_type = "супергруппа (канал+группа)"
        elif is_channel:
            entity_type = "канал"
        elif is_group:
            entity_type = "группа"
        else:
            entity_type = "другое"

        # Определяем, есть ли username (публичный)
        username = getattr(dialog.entity, 'username', None)
        visibility = "публичный" if username else "приватный"

        # Формируем идентификатор для channels.json
        if username:
            identifier = f"t.me/{username}"
        else:
            identifier = f"ID: {dialog.id}"

        print(f"Название: {dialog.name}")
        print(f"  Тип: {entity_type} ({visibility})")
        print(f"  Идентификатор для channels.json: {identifier}")
        print(f"  Внутренний ID: {dialog.id}")
        print("-" * 70)
    
    await client.disconnect()

asyncio.run(main())
