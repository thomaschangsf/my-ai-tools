"""Dispatch logic for PDF-to-Markdown conversion.

Routes input to the appropriate backend:
- arXiv URLs -> arxiv backend (Phase 2)
- Local PDF files -> marker backend (default)
- Local PDF files -> mineru backend (Phase 3, --backend mineru)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversionResult:
    """Result of a PDF-to-Markdown conversion."""

    markdown: str
    images: dict[str, bytes]
    metadata: dict
    source: str
    backend: str


ARXIV_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})"
)


def is_arxiv_url(input_path: str) -> bool:
    return bool(ARXIV_PATTERN.match(input_path))


def extract_arxiv_id(url: str) -> str | None:
    m = ARXIV_PATTERN.match(url)
    return m.group(1) if m else None


def convert(
    input_path: str,
    output_dir: str | None = None,
    backend: str = "marker",
    use_llm: str | None = None,
    llm_model: str | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    force_ocr: bool = False,
    page_range: str | None = None,
) -> ConversionResult:
    """Convert a PDF or arXiv URL to markdown.

    Args:
        input_path: Path to a local PDF or an arXiv URL.
        output_dir: Directory for output files. Defaults to same dir as input.
        backend: Conversion backend ("marker" or "mineru").
        use_llm: LLM provider for enhanced conversion (None for no LLM).
        llm_model: Override the default model for the LLM provider.
        llm_api_key: API key (prefer env vars instead).
        llm_base_url: Base URL for OpenAI-compatible providers.
        force_ocr: Force OCR on all pages.
        page_range: Page range to convert (e.g. "0,5-10,20").

    Returns:
        ConversionResult with markdown, images, and metadata.
    """
    if is_arxiv_url(input_path):
        raise NotImplementedError(
            "arXiv URL conversion is not yet implemented (Phase 2). "
            "Download the PDF and pass the local path instead."
        )

    filepath = Path(input_path).resolve()
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if not filepath.suffix.lower() == ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {filepath.suffix}")

    if backend == "marker":
        return _convert_with_marker(
            filepath=filepath,
            use_llm=use_llm,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            force_ocr=force_ocr,
            page_range=page_range,
        )
    elif backend == "mineru":
        raise NotImplementedError(
            "MinerU backend is not yet implemented (Phase 3). "
            "Use --backend marker (default) instead."
        )
    else:
        raise ValueError(f"Unknown backend: {backend!r}. Supported: marker, mineru")


def _convert_with_marker(
    filepath: Path,
    use_llm: str | None,
    llm_model: str | None,
    llm_api_key: str | None,
    llm_base_url: str | None,
    force_ocr: bool,
    page_range: str | None,
) -> ConversionResult:
    import os
    import sys

    from my_ai_tools.pdf2md.backends.marker import MarkerConfig, convert as marker_convert
    from my_ai_tools.pdf2md.postprocess import cleanup

    # PyTorch MPS has known out-of-bounds indexing bugs with surya/marker.
    # Auto-fallback to CPU if TORCH_DEVICE is not already set.
    if "TORCH_DEVICE" not in os.environ:
        import platform
        if platform.processor() == "arm" or platform.machine() == "arm64":
            os.environ["TORCH_DEVICE"] = "cpu"
            print(
                "Note: Using CPU (TORCH_DEVICE=cpu) due to known MPS compatibility issues.",
                file=sys.stderr,
            )

    config = MarkerConfig(
        force_ocr=force_ocr,
        use_llm=use_llm is not None,
        llm_provider=use_llm,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        page_range=page_range,
    )

    result = marker_convert(filepath, config)
    cleaned_markdown = cleanup(result.markdown)

    return ConversionResult(
        markdown=cleaned_markdown,
        images=result.images,
        metadata=result.metadata,
        source=str(filepath),
        backend="marker",
    )
