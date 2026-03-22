import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('TG_API_ID'))
API_HASH = os.getenv('TG_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))