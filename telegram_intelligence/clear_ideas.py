import sqlite3
conn = sqlite3.connect('tg_messages.db')
conn.execute('DELETE FROM ideas')
conn.commit()
conn.close()
print("Таблица ideas очищена")
