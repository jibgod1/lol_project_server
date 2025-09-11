import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("⚠️ Riot API Key가 설정되지 않았습니다. .env 파일을 확인하세요.")

# %%



