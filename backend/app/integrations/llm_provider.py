import httpx
from typing import Optional
from app.core.config import settings
from app.core.logging import logger

GROQ_MODELS = {
    "fast": "llama-3.1-8b-instant",
    "smart": "llama-3.3-70b-versatile",
}

SYSTEM_PROMPT = """You are a warm, elite personal financial advisor responding via Telegram.

Tone & Style Rules:
- Sound like a helpful, knowledgeable human advisor chatting with a client.
- Always start with a brief, friendly, natural opening statement (e.g. "Sure! Tech valuations are high right now, but here is a simple breakdown of P/E ratios:") rather than jumping straight into dry bullets.
- Use short bullet points (•) with *bold* terms for data, metrics, or options to keep it readable on mobile.
- Limit bullets to a maximum of 5 lines total.
- Conclude naturally, often asking a relevant follow-up question (e.g., "Which specific stock are you looking at right now?") to keep the conversation flowing.
- Keep the overall length concise (suitable for a quick Telegram read).
- Avoid robotic disclaimers unless strictly required by finance compliance."""

class LLMProvider:
    """
    LLM interface supporting Groq (primary), OpenAI, and Gemini.
    Falls back to structured rule-based responses if no API key is available.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.provider = (settings.LLM_PROVIDER or "groq").lower()

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None, fast: bool = True) -> str:
        """
        Sends a prompt to the configured LLM and returns the response text.
        """
        sys = system_prompt or SYSTEM_PROMPT

        if not self.api_key or self.api_key in ("your_llm_api_key_here", ""):
            logger.warning("No LLM API key configured. Using rule-based engine.")
            return None  # Signal to caller to use fallback

        try:
            if "groq" in self.provider:
                return await self._call_groq(prompt, sys, fast)
            elif "openai" in self.provider:
                return await self._call_openai(prompt, sys)
            elif "gemini" in self.provider:
                return await self._call_gemini(prompt, sys)
        except Exception as e:
            logger.warning(f"LLM API call failed ({self.provider}): {str(e)}. Using fallback.")
            return None

        return None

    async def _call_groq(self, prompt: str, system_prompt: str, fast: bool = True) -> Optional[str]:
        model = GROQ_MODELS["fast"] if fast else GROQ_MODELS["smart"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.4
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
            logger.error(f"Groq API error {res.status_code}: {res.text}")
            return None

    async def _call_openai(self, prompt: str, system_prompt: str) -> Optional[str]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.4
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
            return None

    async def _call_gemini(self, prompt: str, system_prompt: str) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}]}
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return None
