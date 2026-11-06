import os
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from character import SYSTEM_INSTRUCTION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zoey_companion")

app = FastAPI(title="Zoey Agent Companion")

BASE_DIR = Path(__file__).resolve().parent
AVATAR_PATH = BASE_DIR / "avatar.jpg"
ENV_PATH = BASE_DIR / ".env"
INDEX_PATH = BASE_DIR / "index.html"

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key and ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
    return key


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []


@app.get("/avatar.jpg")
async def get_avatar():
    if AVATAR_PATH.exists():
        return FileResponse(AVATAR_PATH, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Avatar image not found")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    api_key = get_api_key()

    if api_key:
        try:
            from google import genai
            from google.genai import types

            gemini_client = genai.Client(api_key=api_key)

            contents = []
            for item in request.history[-6:]:
                role = "user" if item.get("role") == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=item.get("text", ""))]))
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.8,
            )

            response = gemini_client.models.generate_content(
                model="gemini-3.5-flash",
                contents=contents,
                config=config,
            )
            return {"reply": response.text.strip()}
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return {"reply": f"Oops, I had a little trouble thinking: {str(e)}"}
    else:
        is_chinese = any("\u4e00" <= char <= "\u9fff" for char in user_message)
        if is_chinese:
            return {
                "reply": "你好呀！我是 Zoey。很高兴见到你！如果想让我使用 Gemini 实时回答，请在运行终端设置 GEMINI_API_KEY 环境变量哦。"
            }
        else:
            return {
                "reply": "Hi there! I'm Zoey, so wonderful to meet you! To enable my live Gemini AI brain, just set your GEMINI_API_KEY environment variable."
            }


@app.get("/", response_class=HTMLResponse)
async def index():
    if INDEX_PATH.exists():
        return HTMLResponse(content=INDEX_PATH.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Zoey Companion: index.html not found</h1>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)
