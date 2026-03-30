import sys
import os
# Добавляем папку telegram_intelligence (для database.py и других модулей внутри)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Добавляем корень проекта (для market_structure_engine)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from telethon import TelegramClient, events, Button
from tv_alert_config import API_ID, API_HASH, BOT_TOKEN, TARGET_CHANNEL, ADMIN_USER_ID
from database import Database

db = Database()
db.create_pending_alerts_table()
db.create_settings_table()
db.add_request_msg_id_column()

client = None

async def publish_alert(text, photo_path=None):
    """Публикация алерта в целевой канал."""
    if db.get_setting('publish_enabled', 'true') == 'false':
        print(f"[PAUSED] Not published: {text[:50]}...")
        return
    if photo_path:
        await client.send_file(TARGET_CHANNEL, photo_path, caption=text)
    else:
        await client.send_message(TARGET_CHANNEL, text)

async def process_pending_alerts():
    """Обработка новых алертов. Если пауза – показываем только кнопку возобновления."""
    while True:
        await asyncio.sleep(5)
        alerts = db.get_pending_alerts_by_user(ADMIN_USER_ID, status='waiting_decision')
        for alert in alerts:
            publish_enabled = db.get_setting('publish_enabled', 'true') == 'true'
            if not publish_enabled:
                # Пауза: показываем сообщение с Resume-кнопкой
                buttons = [[Button.inline("▶️ Возобновить", data=f"resume_{alert['id']}")]]
                msg = await client.send_message(
                    ADMIN_USER_ID,
                    f"⏸ Публикация приостановлена.\nАлерт:\n\n{alert['alert_text']}\n\nНажмите «Возобновить», чтобы обработать.",
                    buttons=buttons
                )
                db.update_pending_alert_request_msg_id(alert['id'], msg.id)
                db.update_pending_alert_status(alert['id'], 'paused')
                continue

            # Обычный режим: кнопки Да/Нет/Пауза/Скип (2x2)
            buttons = [
                [Button.inline("✅ Да (со скрином)", data=f"yes_{alert['id']}"),
                 Button.inline("❌ Нет (без скрина)", data=f"no_{alert['id']}")],
                [Button.inline("⏸ Пауза", data=f"pause_{alert['id']}"),
                 Button.inline("🚫 Не публиковать", data=f"skip_{alert['id']}")]
            ]
            msg = await client.send_message(
                ADMIN_USER_ID,
                f"📈 Новый алерт:\n\n{alert['alert_text']}\n\nВыберите действие:",
                buttons=buttons
            )
            db.update_pending_alert_request_msg_id(alert['id'], msg.id)
            db.update_pending_alert_status(alert['id'], 'waiting_user')

async def check_timeouts():
    while True:
        await asyncio.sleep(10)
        expired = db.get_expired_alerts()
        for alert in expired:
            if alert['status'] in ('waiting_user', 'paused'):
                db.delete_pending_alert(alert['id'])
                await client.send_message(ADMIN_USER_ID, f"⚠️ Алерт удалён по таймауту (без публикации).")
            elif alert['status'] == 'waiting_photo':
                await publish_alert(alert['alert_text'])
                db.delete_pending_alert(alert['id'])
                await client.send_message(ADMIN_USER_ID, f"⚠️ Алерт опубликован без скрина (таймаут фото).")

photo_wait_tasks = {}

async def start_photo_timeout(alert_id, alert_text, retry_count=0):
    await asyncio.sleep(60)
    alert = db.get_pending_alert(alert_id)
    if not alert or alert['status'] != 'waiting_photo':
        return
    if retry_count == 0:
        await client.send_message(
            ADMIN_USER_ID,
            f"⏰ Напоминание: для алерта #{alert_id} нужно отправить фото в течение 60 секунд, иначе он уйдёт без фото.",
            reply_to=alert['request_msg_id']
        )
        task = asyncio.create_task(start_photo_timeout(alert_id, alert_text, retry_count=1))
        photo_wait_tasks[alert_id] = task
    else:
        await publish_alert(alert_text)
        db.delete_pending_alert(alert_id)
        await client.send_message(ADMIN_USER_ID, f"⚠️ Алерт опубликован без скрина (истекло время ожидания).")

async def main():
    global client
    client = TelegramClient('tv_alert_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    os.makedirs('tv_screenshots', exist_ok=True)

    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        user_id = event.sender_id
        if user_id != ADMIN_USER_ID:
            await event.answer("❌ Только для администратора", alert=True)
            return

        data = event.data.decode()
        if data.startswith('yes_'):
            alert_id = int(data.split('_')[1])
            alert = db.get_pending_alert(alert_id)
            if not alert or alert['status'] != 'waiting_user':
                await event.answer("⚠️ Уже обработано", alert=True)
                return
            prompt_msg = await client.send_message(
                ADMIN_USER_ID,
                f"✅ Отправьте фото (скриншот) ответом на это сообщение в течение 60 секунд."
            )
            db.update_pending_alert_status(alert_id, 'waiting_photo')
            db.update_pending_alert_request_msg_id(alert_id, prompt_msg.id)
            task = asyncio.create_task(start_photo_timeout(alert_id, alert['alert_text']))
            photo_wait_tasks[alert_id] = task
            await event.edit(f"✅ Ожидаю фото...")
            await event.answer("Жду фото")
        elif data.startswith('no_'):
            alert_id = int(data.split('_')[1])
            alert = db.get_pending_alert(alert_id)
            if not alert or alert['status'] != 'waiting_user':
                await event.answer("⚠️ Уже обработано", alert=True)
                return
            await publish_alert(alert['alert_text'])
            db.delete_pending_alert(alert_id)
            await event.edit(f"❌ Опубликовано без скрина.")
            await event.answer("Опубликовано")
        elif data.startswith('skip_'):
            alert_id = int(data.split('_')[1])
            alert = db.get_pending_alert(alert_id)
            if not alert or alert['status'] != 'waiting_user':
                await event.answer("⚠️ Уже обработано", alert=True)
                return
            db.delete_pending_alert(alert_id)
            await event.edit(f"🚫 Алерт удалён.")
            await event.answer("Удалён")
        elif data.startswith('pause_'):
            alert_id = int(data.split('_')[1])
            alert = db.get_pending_alert(alert_id)
            if not alert or alert['status'] != 'waiting_user':
                await event.answer("⚠️ Уже обработано", alert=True)
                return
            # Включаем глобальную паузу
            db.set_setting('publish_enabled', 'false')
            # Меняем статус этого алерта на paused
            db.update_pending_alert_status(alert_id, 'paused')
            # Редактируем текущее сообщение: заменяем кнопки на одну кнопку "Возобновить"
            buttons = [[Button.inline("▶️ Возобновить", data=f"resume_{alert_id}")]]
            await event.edit(
                f"⏸ Публикация приостановлена.\nАлерт:\n\n{alert['alert_text']}\n\nНажмите «Возобновить», чтобы обработать.",
                buttons=buttons
            )
            await event.answer("Пауза включена")
        elif data.startswith('resume_'):
            alert_id = int(data.split('_')[1])
            alert = db.get_pending_alert(alert_id)
            if not alert:
                await event.answer("⚠️ Алерт не найден", alert=True)
                return
            # Включаем публикацию
            db.set_setting('publish_enabled', 'true')
            # Переводим алерт в статус waiting_user
            db.update_pending_alert_status(alert_id, 'waiting_user')
            # Обновляем request_msg_id на текущее сообщение
            db.update_pending_alert_request_msg_id(alert_id, event.id)
            # Показываем кнопки прямо в этом сообщении
            buttons = [
                [Button.inline("✅ Да (со скрином)", data=f"yes_{alert_id}"),
                 Button.inline("❌ Нет (без скрина)", data=f"no_{alert_id}")],
                [Button.inline("⏸ Пауза", data=f"pause_{alert_id}"),
                 Button.inline("🚫 Не публиковать", data=f"skip_{alert_id}")]
            ]
            await event.edit(
                f"📈 Новый алерт:\n\n{alert['alert_text']}\n\nВыберите действие:",
                buttons=buttons
            )
            await event.answer("Возобновлено")

    @client.on(events.NewMessage(from_users=ADMIN_USER_ID))
    async def photo_handler(event):
        if not event.message.photo:
            return
        reply_to = event.message.reply_to_msg_id
        if not reply_to:
            return
        alerts = db.get_pending_alerts_by_user(ADMIN_USER_ID, status='waiting_photo')
        for alert in alerts:
            if alert['request_msg_id'] == reply_to:
                if alert['id'] in photo_wait_tasks:
                    photo_wait_tasks[alert['id']].cancel()
                    del photo_wait_tasks[alert['id']]
                path = await event.message.download_media(file=f'tv_screenshots/{alert["id"]}.jpg')
                await publish_alert(alert['alert_text'], path)
                db.delete_pending_alert(alert['id'])
                await event.reply('✅ Опубликовано со скрином.')
                return

    @client.on(events.NewMessage(from_users=ADMIN_USER_ID, pattern='^/start$'))
    async def start_handler(event):
        await event.reply("✅ Бот работает. Используйте /analyze BTC для анализа структуры.")

    @client.on(events.NewMessage(from_users=ADMIN_USER_ID, pattern='^/analyze (\\w+)$'))
    async def analyze_handler(event):
        symbol = event.pattern_match.group(1).upper()
        if not symbol.endswith('/USDT'):
            symbol = f"{symbol}/USDT"
        try:
            from market_structure_engine import DataFetcher, StructureEngine
            
            fetcher = DataFetcher()
            candles = fetcher.fetch_ohlcv(symbol, '1h', limit=200)
            structure = StructureEngine.analyze(symbol, '1h', candles)

            msg = (f"📊 Анализ {symbol} (1h)\n"
                   f"Тренд: {structure.trend.value}\n"
                   f"Поддержки: {', '.join(str(round(l,2)) for l in structure.supports[-3:])}\n"
                   f"Сопротивления: {', '.join(str(round(l,2)) for l in structure.resistances[-3:])}")
            await event.reply(msg)
        except Exception as e:
            await event.reply(f"Ошибка: {e}")

    # Запуск
    asyncio.create_task(process_pending_alerts())
    asyncio.create_task(check_timeouts())

    print("TV Alert Relay запущен. Ожидание алертов...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())