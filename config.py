from dotenv import load_dotenv
import os
from typing import Optional, List

# Загрузка переменных окружения из .env файла
load_dotenv()

TG_TOKEN: Optional[str] = os.environ.get("TG_TOKEN")
ADMIN_ID: Optional[int] = int(os.environ.get("ADMIN_ID"))
CHANEL_ID: Optional[int] = int(os.environ.get("CHANEL_ID"))
