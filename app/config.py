import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "api_key.env")
load_dotenv(dotenv_path)


API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("⚠️ Riot API Key가 설정되지 않았습니다. .env 파일을 확인하세요.")

# %%





# %%



