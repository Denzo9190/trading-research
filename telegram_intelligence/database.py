import sqlite3
from contextlib import contextmanager

class Database:
    """
    Класс для работы с базой данных SQLite.
    Создаёт таблицы messages и ideas при первом запуске.
    """
    def __init__(self, db_path='tg_messages.db'):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Таблица сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    text TEXT,
                    UNIQUE(date, channel, text)
                )
            ''')
            # Таблица извлечённых идей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    asset TEXT,
                    direction TEXT,
                    level REAL,
                    target REAL,
                    text TEXT
                )
            ''')
            conn.commit()

    def insert_message(self, date, channel, text):
        with self.get_connection() as conn:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO messages (date, channel, text)
                    VALUES (?, ?, ?)
                ''', (date, channel, text))
                conn.commit()
            except Exception as e:
                print(f"Ошибка вставки сообщения: {e}")

    def insert_idea(self, date, channel, asset, direction, level, target, text):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO ideas (date, channel, asset, direction, level, target, text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date, channel, asset, direction, level, target, text))
            conn.commit()

    def get_all_messages(self):
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM messages ORDER BY date')
            return cursor.fetchall()

    # --- методы для pending_alerts ---
    def create_pending_alerts_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                         CREATE TABLE IF NOT EXISTS pending_alerts (
                                                                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                       user_id INTEGER NOT NULL,
                                                                       alert_text TEXT NOT NULL,
                                                                       status TEXT DEFAULT 'waiting_decision',
                                                                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                       timeout_seconds INTEGER DEFAULT 60
                         )
                         ''')
            conn.commit()

    def add_pending_alert(self, user_id, alert_text, timeout=60):
        with self.get_connection() as conn:
            cursor = conn.execute('''
                                  INSERT INTO pending_alerts (user_id, alert_text, timeout_seconds)
                                  VALUES (?, ?, ?)
                                  ''', (user_id, alert_text, timeout))
            conn.commit()
            return cursor.lastrowid

    def get_pending_alert(self, alert_id):
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM pending_alerts WHERE id = ?', (alert_id,))
            return cursor.fetchone()

    def get_pending_alerts_by_user(self, user_id, status=None):
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute('SELECT * FROM pending_alerts WHERE user_id = ? AND status = ?', (user_id, status))
            else:
                cursor = conn.execute('SELECT * FROM pending_alerts WHERE user_id = ?', (user_id,))
            return cursor.fetchall()

    def update_pending_alert_status(self, alert_id, status):
        with self.get_connection() as conn:
            conn.execute('UPDATE pending_alerts SET status = ? WHERE id = ?', (status, alert_id))
            conn.commit()

    def delete_pending_alert(self, alert_id):
        with self.get_connection() as conn:
            conn.execute('DELETE FROM pending_alerts WHERE id = ?', (alert_id,))
            conn.commit()

    def get_expired_alerts(self):
        with self.get_connection() as conn:
            cursor = conn.execute('''
                                  SELECT * FROM pending_alerts
                                  WHERE strftime('%s','now') - strftime('%s', created_at) > timeout_seconds
                                  ''')
            return cursor.fetchall()

    def update_pending_alert_timeout(self, alert_id, timeout_seconds):
        with self.get_connection() as conn:
            conn.execute('UPDATE pending_alerts SET timeout_seconds = ? WHERE id = ?', (timeout_seconds, alert_id))
            conn.commit()

    # --- Таблица для настроек ---
    def create_settings_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                         CREATE TABLE IF NOT EXISTS settings (
                                                                 key TEXT PRIMARY KEY,
                                                                 value TEXT NOT NULL
                         )
                         ''')
            conn.commit()
            # Устанавливаем значение по умолчанию, если нет
            conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('publish_enabled', 'true'))
            conn.commit()

    def get_setting(self, key, default=None):
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default

    def set_setting(self, key, value):
        with self.get_connection() as conn:
            conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
            conn.commit()

    # --- Добавляем поле request_msg_id в таблицу pending_alerts, если его нет ---
    def add_request_msg_id_column(self):
        with self.get_connection() as conn:
            try:
                conn.execute('ALTER TABLE pending_alerts ADD COLUMN request_msg_id INTEGER')
                conn.commit()
            except sqlite3.OperationalError:
                pass  # колонка уже существует

    def update_pending_alert_request_msg_id(self, alert_id, msg_id):
        with self.get_connection() as conn:
            conn.execute('UPDATE pending_alerts SET request_msg_id = ? WHERE id = ?', (msg_id, alert_id))
            conn.commit()