import base64
import json
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger("gemini")
settings = get_settings()
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
IMAGEN_MODEL = "imagen-3.0-generate-002"


class GeminiService:
    def __init__(self) -> None:
        self._api_key = settings.gemini_api_key
        self._content_model = settings.gemini_content_model
        self._image_models = [
            settings.gemini_image_model,
            "gemini-2.0-flash-preview-image-generation",
        ]

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _post(self, model: str, payload: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Gemini API key is not configured")

        url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, params={"key": self._api_key}, json=payload)
            response.raise_for_status()
            return response.json()

    def _predict_imagen(self, prompt: str) -> bytes | None:
        if not self.is_configured():
            return None

        url = f"{GEMINI_API_BASE}/models/{IMAGEN_MODEL}:predict"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "16:9"},
        }
        try:
            with httpx.Client(timeout=180.0) as client:
                response = client.post(url, params={"key": self._api_key}, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning("imagen_predict_failed error=%s", exc)
            return None

        for prediction in data.get("predictions", []):
            encoded = prediction.get("bytesBase64Encoded")
            if encoded:
                return base64.b64decode(encoded)
        return None

    def chat_json(self, system: str, user: str, max_output_tokens: int = 8192) -> dict[str, Any]:
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.55,
                "maxOutputTokens": max_output_tokens,
            },
        }
        data = self._post(self._content_model, payload, timeout=240.0)
        text = self._extract_text(data)
        return json.loads(text)

    def generate_image_bytes(self, prompt: str, seed: int = 0) -> bytes | None:
        full_prompt = (
            f"{prompt}. Photorealistic, respectful Hindu puja ceremony, natural lighting, "
            f"vibrant marigold flowers, traditional altar, unique composition seed {seed}, "
            "no text, no watermark, no logos."
        )

        image_bytes = self._predict_imagen(full_prompt)
        if image_bytes:
            logger.info("image_generated_via_imagen")
            return image_bytes

        for model in self._image_models:
            image_bytes = self._generate_content_image(model, full_prompt)
            if image_bytes:
                logger.info("image_generated_via_gemini model=%s", model)
                return image_bytes

        return None

    def _generate_content_image(self, model: str, prompt: str) -> bytes | None:
        payload = {
            "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }
        try:
            data = self._post(model, payload, timeout=180.0)
        except Exception as exc:
            logger.warning("gemini_image_model_failed model=%s error=%s", model, exc)
            return None

        for part in self._iter_parts(data):
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            encoded = inline.get("data")
            if encoded:
                return base64.b64decode(encoded)
        return None

    @staticmethod
    def generate_pollinations_image(prompt: str, seed: int = 0, model: str = "flux") -> bytes | None:
        """Photorealistic fallback when Gemini image APIs are unavailable."""
        encoded = quote(prompt[:400])
        urls = [
            (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1344&height=768&nologo=true&seed={seed}&model={model}&enhance=true"
            ),
            (
                f"https://pollinations.ai/p/{encoded}"
                f"?width=1200&height=630&nologo=true&seed={seed}&model={model}"
            ),
        ]
        headers = {"User-Agent": "NamanPuja/1.0"}
        for url in urls:
            for attempt in range(3):
                try:
                    with httpx.Client(timeout=180.0, follow_redirects=True, headers=headers) as client:
                        response = client.get(url)
                        content_type = response.headers.get("content-type", "")
                        if response.status_code == 200 and (
                            "image" in content_type or response.content[:3] == b"\xff\xd8\xff"
                        ):
                            return response.content
                except Exception as exc:
                    logger.warning(
                        "pollinations_image_failed model=%s attempt=%s error=%s",
                        model,
                        attempt,
                        exc,
                    )
                time.sleep(2 + attempt)
        return None

    @staticmethod
    def _iter_parts(data: dict[str, Any]) -> list[dict[str, Any]]:
        parts: list[dict[str, Any]] = []
        for candidate in data.get("candidates", []):
            content = candidate.get("content") or {}
            parts.extend(content.get("parts", []))
        return parts

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        chunks: list[str] = []
        for part in GeminiService._iter_parts(data):
            if "text" in part:
                chunks.append(part["text"])
        if not chunks:
            raise ValueError("Gemini response contained no text")
        return "".join(chunks).strip()


gemini_service = GeminiService()
