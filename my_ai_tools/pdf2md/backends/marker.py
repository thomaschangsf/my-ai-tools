"""Marker backend for local PDF-to-Markdown conversion.

Uses the marker-pdf library with MPS acceleration on Apple Silicon.
Models are downloaded on first run (~1 GB) and cached locally.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


@dataclass
class MarkerResult:
    markdown: str
    images: dict[str, bytes]
    metadata: dict[str, Any]


def _images_to_bytes(images: dict) -> dict[str, bytes]:
    """Convert PIL Image objects from Marker into raw bytes for saving."""
    result: dict[str, bytes] = {}
    for name, img in images.items():
        if isinstance(img, bytes):
            result[name] = img
        else:
            buf = io.BytesIO()
            fmt = "JPEG" if name.lower().endswith((".jpg", ".jpeg")) else "PNG"
            img.save(buf, format=fmt)
            result[name] = buf.getvalue()
    return result


@dataclass
class MarkerConfig:
    """Configuration for the Marker backend."""

    output_format: str = "markdown"
    force_ocr: bool = False
    use_llm: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    page_range: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_marker_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "output_format": self.output_format,
            "force_ocr": self.force_ocr,
            "use_llm": self.use_llm,
        }
        if self.page_range:
            config["page_range"] = self.page_range

        if self.use_llm and self.llm_provider:
            llm_config = _build_llm_config(
                provider=self.llm_provider,
                model=self.llm_model,
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
            )
            config.update(llm_config)

        config.update(self.extra)
        return config


_LLM_SERVICES = {
    "gemini": "marker.services.gemini.GoogleGeminiService",
    "ollama": "marker.services.ollama.OllamaService",
    "openai": "marker.services.openai.OpenAIService",
    "claude": "marker.services.claude.ClaudeService",
    "azure": "marker.services.azure_openai.AzureOpenAIService",
    "vertex": "marker.services.vertex.GoogleVertexService",
}

_KEY_ENV_VARS = {
    "gemini": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "azure": "AZURE_API_KEY",
}

_KEY_SETUP_URLS = {
    "gemini": "https://aistudio.google.com/apikey",
    "openai": "https://platform.openai.com/api-keys",
    "claude": "https://console.anthropic.com/settings/keys",
}


def _build_llm_config(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Build Marker LLM configuration for the given provider."""
    if provider not in _LLM_SERVICES:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            f"Supported: {', '.join(_LLM_SERVICES)}"
        )

    config: dict[str, Any] = {"llm_service": _LLM_SERVICES[provider]}

    if api_key is None and provider in _KEY_ENV_VARS:
        api_key = os.environ.get(_KEY_ENV_VARS[provider])
        if not api_key:
            fallback = os.environ.get("LLM_API_KEY")
            if fallback:
                api_key = fallback
            else:
                url = _KEY_SETUP_URLS.get(provider, "your provider")
                raise EnvironmentError(
                    f"--use-llm {provider} requires {_KEY_ENV_VARS[provider]} "
                    f"environment variable.\nGet a key at: {url}"
                )

    if provider == "gemini":
        if api_key:
            config["gemini_api_key"] = api_key
        if model:
            config["gemini_model"] = model
    elif provider == "ollama":
        config["ollama_base_url"] = base_url or "http://localhost:11434"
        if model:
            config["ollama_model"] = model
    elif provider == "openai":
        if api_key:
            config["openai_api_key"] = api_key
        if model:
            config["openai_model"] = model
        if base_url:
            config["openai_base_url"] = base_url
    elif provider == "claude":
        if api_key:
            config["claude_api_key"] = api_key
        if model:
            config["claude_model_name"] = model
    elif provider == "azure":
        if api_key:
            config["azure_api_key"] = api_key
        if base_url:
            config["azure_endpoint"] = base_url
        if model:
            config["deployment_name"] = model

    return config


_cached_model_dict: dict[str, Any] | None = None


def _get_model_dict() -> dict[str, Any]:
    """Lazily load and cache the Marker model dictionary."""
    global _cached_model_dict
    if _cached_model_dict is None:
        _cached_model_dict = create_model_dict()
    return _cached_model_dict


def convert(filepath: str | Path, config: MarkerConfig | None = None) -> MarkerResult:
    """Convert a PDF file to markdown using Marker.

    Args:
        filepath: Path to the PDF file.
        config: Optional configuration. Uses defaults if not provided.

    Returns:
        MarkerResult with markdown text, images dict, and metadata.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"PDF not found: {filepath}")

    cfg = config or MarkerConfig()
    marker_cfg = cfg.to_marker_config()

    config_parser = ConfigParser(marker_cfg)
    artifact_dict = _get_model_dict()

    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=artifact_dict,
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
        llm_service=config_parser.get_llm_service(),
    )

    rendered = converter(str(filepath))
    text, _, images = text_from_rendered(rendered)

    metadata = {}
    if hasattr(rendered, "metadata"):
        metadata = rendered.metadata if isinstance(rendered.metadata, dict) else {}

    return MarkerResult(markdown=text, images=_images_to_bytes(images), metadata=metadata)
