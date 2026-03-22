import sqlite3

conn = sqlite3.connect('tg_messages.db')
cursor = conn.execute('SELECT channel, text FROM messages LIMIT 20')
for row in cursor:
    print(f"Канал: {row[0]}")
    print(f"Текст: {row[1][:200]}...")  # первые 200 символов
    print("-" * 60)
conn.close()
