"""
Module: llm_client.py
Purpose: Unified LLM client for both Groq (GPT-OSS-120B) and Ollama (Qwen 3.5).

Both providers use OpenAI-compatible APIs, so we wrap the openai SDK
with provider-specific configurations. Includes retry logic for rate limits.
"""

import base64
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from backend.config import settings
from backend.models.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds


class LLMClient:
    """
    Unified client for LLM inference via Groq and Ollama.

    Provides two clients:
        - groq_client: GPT-OSS-120B for reasoning/schema mapping
        - ollama_client: Qwen 3.5 0.8B for vision/image analysis

    Both use OpenAI-compatible APIs.
    """

    def __init__(self):
        self._groq_client: Optional[OpenAI] = None
        self._ollama_client: Optional[OpenAI] = None
        self._llm_call_count = 0

    @property
    def groq_client(self) -> OpenAI:
        """Lazy-initialized Groq client."""
        if self._groq_client is None:
            if not settings.groq_api_key:
                raise LLMError(
                    "GROQ_API_KEY not set. Please add it to your .env file."
                )
            self._groq_client = OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
            )
            logger.info("Groq client initialized")
        return self._groq_client

    @property
    def ollama_client(self) -> OpenAI:
        """Lazy-initialized Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = OpenAI(
                api_key="ollama",  # Ollama doesn't need a real key
                base_url=settings.ollama_base_url,
            )
            logger.info("Ollama client initialized")
        return self._ollama_client

    @property
    def call_count(self) -> int:
        """Total LLM API calls made."""
        return self._llm_call_count

    def chat_groq(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send a chat request to Groq (GPT-OSS-120B).

        Args:
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature (default: 0.1 for determinism)
            max_tokens: Maximum response tokens
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Response text from the model

        Raises:
            LLMRateLimitError: If rate limit is hit after retries
            LLMConnectionError: If API is unreachable
            LLMError: For other API errors
        """
        return self._chat_with_retry(
            client=self.groq_client,
            model=settings.groq_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            provider="Groq",
        )

    def chat_ollama(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """
        Send a chat request to Ollama (Qwen 3.5 0.8B).

        Args:
            messages: Chat messages (can include image content)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            Response text from the model
        """
        return self._chat_with_retry(
            client=self.ollama_client,
            model=settings.ollama_vision_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=None,
            provider="Ollama",
        )

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """
        Analyze an image using Qwen 3.5 vision via Ollama.

        Args:
            image_path: Path to the image file
            prompt: Text prompt to guide analysis
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            Analysis text from the model
        """
        # Encode image to base64
        image_data = self._encode_image(image_path)
        if not image_data:
            raise LLMError(f"Could not read image: {image_path}")

        # Determine MIME type
        suffix = Path(image_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(suffix, "image/jpeg")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ]

        return self.chat_ollama(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _chat_with_retry(
        self,
        client: OpenAI,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
        provider: str,
    ) -> str:
        """
        Execute a chat completion with retry logic for rate limits.

        Implements exponential backoff: 2s, 4s, 8s between retries.
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = client.chat.completions.create(**kwargs)
                self._llm_call_count += 1

                content = response.choices[0].message.content
                if content is None:
                    content = ""

                logger.debug(
                    f"[{provider}] Response received "
                    f"(tokens: {response.usage.total_tokens if response.usage else 'N/A'})"
                )

                return content.strip()

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Rate limit handling
                if "429" in str(e) or "rate" in error_str:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"[{provider}] Rate limited (attempt {attempt + 1}/{MAX_RETRIES}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue

                # Connection errors
                if "connection" in error_str or "refused" in error_str:
                    raise LLMConnectionError(
                        f"{provider} is unreachable. "
                        + (
                            "Is Ollama running? (ollama serve)"
                            if provider == "Ollama"
                            else "Check your internet connection and API key."
                        )
                    ) from e

                # Other errors — don't retry
                raise LLMError(
                    f"{provider} API error: {e}"
                ) from e

        # All retries exhausted
        raise LLMRateLimitError(
            provider=provider,
            retry_after=RETRY_BASE_DELAY * (2 ** MAX_RETRIES),
        )

    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encode image file to base64 string."""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return None

    def check_ollama_health(self) -> bool:
        """Check if Ollama is running and the vision model is available."""
        try:
            response = self.ollama_client.models.list()
            models = [m.id for m in response.data]
            model_available = settings.ollama_vision_model in models
            if not model_available:
                logger.warning(
                    f"Ollama is running but model '{settings.ollama_vision_model}' "
                    f"not found. Available: {models}. "
                    f"Run: ollama pull {settings.ollama_vision_model}"
                )
            return model_available
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def check_groq_health(self) -> bool:
        """Check if Groq API is reachable."""
        try:
            response = self.groq_client.models.list()
            return True
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False


# Singleton instance
llm_client = LLMClient()
