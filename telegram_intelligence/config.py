import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('TG_API_ID', 0))
API_HASH = os.getenv('TG_API_HASH', '')
