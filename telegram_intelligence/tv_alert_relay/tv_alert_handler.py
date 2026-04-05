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

    @client.on(events.NewMessage(from_users=ADMIN_USER_ID, pattern='^/analyze$'))
    async def analyze_no_param_handler(event):
        await event.reply("📊 Используйте: /analyze <символ> [таймфрейм]\n"
                          "Таймфреймы: 1m, 5m, 15m, 30m, 1h, 4h, 1d\n"
                          "Пример: `/analyze BTC 4h`")

    @client.on(events.NewMessage(from_users=ADMIN_USER_ID, pattern='^/analyze (\\w+)(?: (\\w+))?$'))
    async def analyze_handler(event):
        symbol = event.pattern_match.group(1).upper()
        timeframe = event.pattern_match.group(2) or '1h'
        allowed_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if timeframe not in allowed_timeframes:
            await event.reply(f"❌ Неподдерживаемый таймфрейм. Используйте: {', '.join(allowed_timeframes)}")
            return

        if not symbol.endswith('/USDT'):
            symbol = f"{symbol}/USDT"

        try:
            from market_structure_engine import DataFetcher, StructureEngine
            from market_structure_engine.liquidity_engine import LiquidityMapEngine

            fetcher = DataFetcher()
            candles = fetcher.fetch_ohlcv(symbol, timeframe, limit=200)
            structure = StructureEngine.analyze(symbol, timeframe, candles)

            current_price = candles[-1].close

            def cluster_levels(levels, tolerance=0.002):
                if not levels:
                    return []
                levels = sorted(levels)
                clusters = []
                current_cluster = [levels[0]]
                for lvl in levels[1:]:
                    if (lvl - current_cluster[-1]) / current_cluster[-1] < tolerance:
                        current_cluster.append(lvl)
                    else:
                        clusters.append((min(current_cluster), max(current_cluster)))
                        current_cluster = [lvl]
                clusters.append((min(current_cluster), max(current_cluster)))
                return clusters

            supports_raw = [s for s in structure.supports if s < current_price]
            resistances_raw = [r for r in structure.resistances if r > current_price]

            support_zones = cluster_levels(supports_raw)
            resistance_zones = cluster_levels(resistances_raw)

            support_zones.sort(key=lambda z: current_price - z[1], reverse=True)
            resistance_zones.sort(key=lambda z: z[0] - current_price)

            near_supports = support_zones[:3]
            near_resistances = resistance_zones[:3]

            def annotate_zone(z, levels):
                count = sum(1 for l in levels if z[0] <= l <= z[1])
                return " 💪 (сильная)" if count >= 3 else ""

            msg = (f"📊 {symbol} ({timeframe})\n"
                   f"Текущая цена: {current_price:.0f} ⚪\n"
                   f"Тренд: {structure.trend.value}\n")

            if near_supports:
                msg += "🟢 Ближайшие поддержки:\n"
                for i, (low, high) in enumerate(near_supports):
                    if low == high:
                        item = f"уровень {low:.0f}"
                    else:
                        item = f"зона {low:.0f}–{high:.0f}"
                    annotation = annotate_zone((low, high), supports_raw)
                    msg += f"  {i+1}. {item}{annotation}\n"
            else:
                msg += "🟢 Ближайших поддержек не найдено\n"

            if near_resistances:
                msg += "⚫ Ближайшие сопротивления:\n"
                for i, (low, high) in enumerate(near_resistances):
                    if low == high:
                        item = f"уровень {low:.0f}"
                    else:
                        item = f"зона {low:.0f}–{high:.0f}"
                    annotation = annotate_zone((low, high), resistances_raw)
                    msg += f"  {i+1}. {item}{annotation}\n"
            else:
                msg += "⚫ Ближайших сопротивлений не найдено\n"

            # ========== LIQUIDITY MAP ==========

            # Передаём в движок уже отфильтрованные и кластеризованные уровни
            resistance_levels = [high for (low, high) in near_resistances]
            support_levels = [low for (low, high) in near_supports]
            # ========== LIQUIDITY MAP ENGINE v0.2 ==========
            liquidity_data = LiquidityMapEngine.analyze(
                structure,
                current_price=current_price,
                lookback=100,
                max_distance_pct=0.0025,
                max_width_pct=0.0035,
                sweep_lookback=5
            )

            # Фильтруем зоны ликвидности по направлению (только впереди цены)
            nearby_zones = []
            for zone in liquidity_data["zones"]:
                if zone.zone_type in ("equal_high", "swing_high", "above_resistance"):   # типы, где зона над ценой
                    if zone.zone_low > current_price:
                        nearby_zones.append(zone)
                elif zone.zone_type in ("equal_low", "swing_low", "below_support"):      # типы, где зона под ценой
                    if zone.zone_high < current_price:
                        nearby_zones.append(zone)

            if nearby_zones:
                msg += "\n⚡ Ближайшие зоны ликвидности:\n"
                for zone in nearby_zones[:3]:
                    # Определяем подпись в зависимости от touch_count
                    if zone.zone_type in ("equal_high", "swing_high", "above_resistance"):
                        if zone.touch_count >= 3:
                            zone_label = "equal highs"
                        elif zone.touch_count == 2:
                            zone_label = "liquidity cluster"
                        else:
                            zone_label = "liquidity zone"  # fallback
                    elif zone.zone_type in ("equal_low", "swing_low", "below_support"):
                        if zone.touch_count >= 3:
                            zone_label = "equal lows"
                        elif zone.touch_count == 2:
                            zone_label = "liquidity cluster"
                        else:
                            zone_label = "liquidity zone"
                    else:
                        zone_label = zone.zone_type.replace('_', ' ')
                    msg += f"  • {zone_label}: {zone.zone_low:.0f}–{zone.zone_high:.0f} (касаний: {zone.touch_count})\n"

            if liquidity_data["sweeps"]:
                msg += "\n🧹 Свежие свипы ликвидности:\n"
                for sweep in liquidity_data["sweeps"][:3]:
                    zone = sweep.zone
                    zone_desc = zone.zone_type.replace('_', ' ')
                    msg += f"  • {zone_desc} на {zone.zone_low:.0f}–{zone.zone_high:.0f} ({sweep.sweep_type})\n"

            # ========== IMBALANCE ENGINE ==========
            from market_structure_engine.imbalance_engine import ImbalanceEngine
            imbalance_data = ImbalanceEngine.analyze(
                structure,
                min_size_atr=0.35,
                max_distance_atr=2.5
            )
            if imbalance_data["fvgs"]:
                msg += "\n⚡ Imbalances (FVG):\n"
                for fvg in imbalance_data["fvgs"][:3]:
                    if fvg.type == "bearish":
                        direction = "шорт FVG"
                    else:
                        direction = "лонг FVG"
                    msg += f"  • {direction}: {fvg.price_low:.0f}–{fvg.price_high:.0f} ({fvg.age} св. назад)\n"

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