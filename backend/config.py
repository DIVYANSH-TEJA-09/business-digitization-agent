"""
Module: config.py
Purpose: Centralized configuration management using pydantic-settings.

Loads environment variables from .env file for Groq API, Ollama,
storage paths, and processing settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # --- Groq API (GPT-OSS-120B for reasoning/schema mapping) ---
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq API base URL"
    )
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        description="Groq model identifier"
    )

    # --- Ollama (Qwen 3.5 0.8B for vision) ---
    ollama_base_url: str = Field(
        default="https://ollama.cloud/v1",
        description="Ollama API base URL"
    )
    ollama_vision_model: str = Field(
        default="qwen3.5:0.8b",
        description="Ollama vision model name"
    )
    ollama_api_key: str = Field(
        default="",
        description="Ollama Cloud API key"
    )

    # --- Storage Paths ---
    upload_dir: str = Field(default="storage/uploads")
    extracted_dir: str = Field(default="storage/extracted")
    profiles_dir: str = Field(default="storage/profiles")
    index_dir: str = Field(default="storage/index")
    media_dir: str = Field(default="storage/media")

    # --- Processing Settings ---
    max_zip_size_mb: int = Field(default=500, ge=1)
    max_concurrent_parsers: int = Field(default=4, ge=1)
    log_level: str = Field(default="INFO")

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_upload_path(self) -> Path:
        return PROJECT_ROOT / self.upload_dir

    def get_extracted_path(self) -> Path:
        return PROJECT_ROOT / self.extracted_dir

    def get_profiles_path(self) -> Path:
        return PROJECT_ROOT / self.profiles_dir

    def get_index_path(self) -> Path:
        return PROJECT_ROOT / self.index_dir

    def get_media_path(self) -> Path:
        return PROJECT_ROOT / self.media_dir


# Singleton settings instance
settings = Settings()
