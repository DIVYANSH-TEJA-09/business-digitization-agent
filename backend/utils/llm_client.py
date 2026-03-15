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
        self._ollama_models_cached: Optional[List[str]] = None
        self._groq_api_key_validated = False
        logger.info("[LLMClient] Initializing LLM client...")

    @property
    def groq_client(self) -> OpenAI:
        """Lazy-initialized Groq client."""
        if self._groq_client is None:
            logger.info("[LLMClient] Initializing Groq client...")
            if not settings.groq_api_key or settings.groq_api_key.startswith("your_"):
                logger.warning("[LLMClient] GROQ_API_KEY not set or using placeholder. Groq features will be unavailable.")
                # Create a dummy client that will fail gracefully
                self._groq_client = OpenAI(
                    api_key="sk-dummy-key",
                    base_url=settings.groq_base_url,
                )
            else:
                self._groq_client = OpenAI(
                    api_key=settings.groq_api_key.strip(),
                    base_url=settings.groq_base_url,
                )
                logger.info(f"[LLMClient] Groq client initialized with API key (model: {settings.groq_model})")
            logger.info(f"[LLMClient] Groq client initialized (model: {settings.groq_model})")
        return self._groq_client

    @property
    def ollama_client(self) -> OpenAI:
        """Lazy-initialized Ollama client."""
        if self._ollama_client is None:
            logger.info(f"[LLMClient] Initializing Ollama client ({settings.ollama_base_url})...")
            # Use API key from settings if available (for Ollama Cloud)
            api_key = settings.ollama_api_key if settings.ollama_api_key else "ollama"
            self._ollama_client = OpenAI(
                api_key=api_key,
                base_url=settings.ollama_base_url,
            )
            logger.info(f"[LLMClient] Ollama client initialized (model: {settings.ollama_vision_model})")
            
            # Verify model is available
            try:
                models = self._get_ollama_models()
                if settings.ollama_vision_model not in models:
                    logger.warning(
                        f"[LLMClient] Model '{settings.ollama_vision_model}' not found in Ollama. "
                        f"Available models: {models}. "
                        f"Run: ollama pull {settings.ollama_vision_model}"
                    )
                else:
                    logger.info(f"[LLMClient] Model '{settings.ollama_vision_model}' is available")
            except Exception as e:
                logger.warning(f"[LLMClient] Could not verify Ollama models: {e}")
                
        return self._ollama_client

    def _get_ollama_models(self) -> List[str]:
        """Get list of available Ollama models (cached)."""
        if self._ollama_models_cached is not None:
            return self._ollama_models_cached
        
        try:
            response = self.ollama_client.models.list()
            self._ollama_models_cached = [m.id for m in response.data]
            logger.info(f"[LLMClient] Found {len(self._ollama_models_cached)} Ollama models: {self._ollama_models_cached}")
            return self._ollama_models_cached
        except Exception as e:
            logger.error(f"[LLMClient] Failed to list Ollama models: {e}")
            return []

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
        logger.info(f"[LLMClient] Analyzing image: {Path(image_path).name}")
        
        # Encode image to base64
        image_data = self._encode_image(image_path)
        if not image_data:
            logger.error(f"[LLMClient] Could not read image: {image_path}")
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

        logger.info(f"[LLMClient] Sending vision request to Ollama (model: {settings.ollama_vision_model})")
        result = self.chat_ollama(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"[LLMClient] Vision analysis complete for {Path(image_path).name}")
        return result

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
                }
                
                # Reasoning models (like gpt-oss-120b) require specific parameters
                if "gpt-oss-120b" in model.lower() or "o1" in model.lower() or "o3" in model.lower():
                    kwargs["temperature"] = 1
                    kwargs["top_p"] = 1
                    kwargs["max_completion_tokens"] = 8192
                    kwargs["reasoning_effort"] = "medium"
                    kwargs["stop"] = None
                    kwargs["stream"] = True
                else:
                    kwargs["temperature"] = temperature
                    kwargs["max_tokens"] = max_tokens

                if response_format:
                    kwargs["response_format"] = response_format

                response = client.chat.completions.create(**kwargs)
                self._llm_call_count += 1

                if kwargs.get("stream"):
                    content = ""
                    tokens = "N/A (stream)"
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content += chunk.choices[0].delta.content
                else:
                    content = response.choices[0].message.content
                    tokens = response.usage.total_tokens if hasattr(response, "usage") and response.usage else "N/A"

                if content is None:
                    content = ""

                logger.debug(
                    f"[{provider}] Response received (tokens: {tokens})"
                )

                return content.strip()

            except Exception as e:
                error_str = str(e).lower()
                last_error = e
                
                # Check for API key errors
                if "401" in str(e) or "invalid_api_key" in error_str or "unauthorized" in error_str:
                    logger.error(
                        f"[{provider}] API Key Error: The API key is invalid or expired. "
                        f"Please check your .env file and ensure GROQ_API_KEY is correct. "
                        f"Get a new key from: https://console.groq.com/keys"
                    )
                    raise LLMError(
                        f"{provider} API key is invalid. "
                        f"Please check your .env file and visit https://console.groq.com/keys"
                    ) from e

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
        logger.info("[LLMClient] Checking Ollama health...")
        try:
            models = self._get_ollama_models()
            model_available = settings.ollama_vision_model in models
            if model_available:
                logger.info(f"[LLMClient] Ollama health check PASSED - model '{settings.ollama_vision_model}' available")
            else:
                logger.warning(
                    f"[LLMClient] Ollama is running but model '{settings.ollama_vision_model}' "
                    f"not found. Available: {models}. "
                    f"Run: ollama pull {settings.ollama_vision_model}"
                )
            return model_available
        except Exception as e:
            logger.error(f"[LLMClient] Ollama health check FAILED: {e}")
            return False

    def check_groq_health(self) -> bool:
        """Check if Groq API is reachable."""
        logger.info("[LLMClient] Checking Groq health...")
        try:
            response = self.groq_client.models.list()
            logger.info("[LLMClient] Groq health check PASSED")
            return True
        except Exception as e:
            logger.error(f"[LLMClient] Groq health check FAILED: {e}")
            return False


# Singleton instance
llm_client = LLMClient()
