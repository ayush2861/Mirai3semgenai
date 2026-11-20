import os
import time
import logging
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError, APIError

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini API provider using official google-genai SDK.
    Supports configurable models, automatic retries with exponential backoff on 503/429,
    fallback model degradation, and token usage tracking.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.primary_model = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        
        # Parse fallback models
        fallback_str = settings.GEMINI_FALLBACK_MODELS or "gemini-3.5-flash-lite,gemini-3.5-flash"
        self.candidate_models = [m.strip() for m in fallback_str.split(",") if m.strip()]
        if self.primary_model not in self.candidate_models:
            self.candidate_models.insert(0, self.primary_model)

        self._client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with primary model: '{self.primary_model}'.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    def is_available(self) -> bool:
        return bool(self.api_key and self._client is not None)

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured or client is unavailable.")

        last_error = None

        # Iterate through model candidates with retries
        for model_name in self.candidate_models:
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(f"Calling Gemini API with model='{model_name}' (attempt {attempt + 1})...")

                    config_params = {
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    }
                    if system_instruction:
                        config_params["system_instruction"] = system_instruction

                    generate_config = types.GenerateContentConfig(**config_params)

                    response = self._client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=generate_config
                    )

                    response_text = response.text or ""
                    
                    # Extract token metrics if available
                    prompt_tokens = None
                    candidates_tokens = None
                    total_tokens = None
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        um = response.usage_metadata
                        prompt_tokens = getattr(um, "prompt_token_count", None)
                        candidates_tokens = getattr(um, "candidates_token_count", None)
                        total_tokens = getattr(um, "total_token_count", None)

                    return {
                        "text": response_text.strip(),
                        "model": model_name,
                        "prompt_tokens": prompt_tokens,
                        "candidates_tokens": candidates_tokens,
                        "total_tokens": total_tokens
                    }

                except (ServerError, ClientError, APIError) as api_err:
                    last_error = api_err
                    status_code = getattr(api_err, "code", getattr(api_err, "status_code", None))
                    logger.warning(
                        f"Gemini API warning for model '{model_name}' (status={status_code}): {api_err}. "
                        f"Attempt {attempt + 1}/{max_retries + 1}."
                    )

                    # Backoff on 503 or 429
                    if status_code in (503, 429) and attempt < max_retries:
                        sleep_secs = (attempt + 1) * 1.5
                        time.sleep(sleep_secs)
                        continue
                    else:
                        # Try next fallback model candidate
                        break

                except Exception as ex:
                    last_error = ex
                    logger.error(f"Unexpected error during Gemini generation on model '{model_name}': {ex}")
                    break

        raise RuntimeError(f"Gemini generation failed across all available models. Last error: {str(last_error)}")

gemini_provider = GeminiProvider()
