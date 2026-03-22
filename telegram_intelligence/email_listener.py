import sys
import os
import imaplib
import email
import time
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
IMAP_FOLDER = os.getenv('IMAP_FOLDER', 'TradingView')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    print("Ошибка: EMAIL_ADDRESS или EMAIL_PASSWORD не заданы в .env")
    sys.exit(1)

try:
    ADMIN_USER_ID = int(ADMIN_USER_ID)
except:
    print("Ошибка: ADMIN_USER_ID должен быть числом")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import Database

db = Database()
db.create_pending_alerts_table()

def clean_text(text):
    if text is None:
        return ''
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        return text.strip()
    except:
        return str(text)

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                payload = part.get_payload(decode=True)
                return clean_text(payload)
    else:
        payload = msg.get_payload(decode=True)
        return clean_text(payload)
    return ''

def fetch_tradingview_emails():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("Подключение к почте успешно")

        folder = IMAP_FOLDER if IMAP_FOLDER else 'INBOX'
        try:
            mail.select(folder)
            print(f"Выбрана папка: {folder}")
        except Exception:
            print(f"Папка '{folder}' не найдена, переключаемся на INBOX")
            mail.select('INBOX')

        result, data = mail.search(None, '(FROM "noreply@tradingview.com")')
        if result != 'OK':
            print("Не удалось выполнить поиск писем от TradingView")
            mail.close()
            mail.logout()
            return

        found = data[0].split()
        print(f"Найдено писем от noreply@tradingview.com: {len(found)}")

        for num in found:
            result, msg_data = mail.fetch(num, '(RFC822)')
            if result != 'OK':
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_header(msg.get('Subject', ''))[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode('utf-8', errors='replace')
            from_addr = msg.get('From')
            print(f"Обрабатывается письмо: {subject} от {from_addr}")

            body = get_email_body(msg)
            alert_text = f"Alert from TradingView\nSubject: {subject}\n\n{body}"
            db.add_pending_alert(ADMIN_USER_ID, alert_text, timeout=60)
            print(f"Добавлен алерт: {subject[:50]}...")

            # Помечаем для удаления
            mail.store(num, '+FLAGS', '\\Deleted')

        # Удаляем помеченные письма
        mail.expunge()
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Ошибка при работе с почтой: {e}")

def main():
    print("Email listener запущен. Ожидание писем от TradingView...")
    while True:
        fetch_tradingview_emails()
        time.sleep(30)

if __name__ == '__main__':
    main()