"""CLI entry point for pdf2md.

Usage:
    uv run pdf2md convert ./paper.pdf
    uv run pdf2md convert ./paper.pdf --output ./notes/
    uv run pdf2md convert ./paper.pdf --use-llm ollama
    uv run pdf2md convert ./paper.pdf --use-llm gemini
    uv run pdf2md --help
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="pdf2md",
    help="Convert PDFs to clean Markdown with LaTeX equation support.",
    no_args_is_help=True,
)


@app.command()
def convert(
    input_path: str = typer.Argument(
        ...,
        help="Path to a PDF file, directory of PDFs, or arXiv URL.",
    ),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output directory. Defaults to same directory as input file.",
    ),
    backend: str = typer.Option(
        "marker",
        "--backend", "-b",
        help="Conversion backend: marker (default) or mineru.",
    ),
    use_llm: str = typer.Option(
        None,
        "--use-llm",
        help="LLM provider for enhanced accuracy: ollama, gemini, openai, claude, azure.",
    ),
    llm_model: str = typer.Option(
        None,
        "--llm-model",
        help="Override default model for the LLM provider.",
    ),
    llm_base_url: str = typer.Option(
        None,
        "--llm-base-url",
        help="Base URL for OpenAI-compatible API endpoints.",
    ),
    force_ocr: bool = typer.Option(
        False,
        "--force-ocr",
        help="Force OCR on all pages (useful for scanned PDFs or inline math).",
    ),
    page_range: str = typer.Option(
        None,
        "--page-range",
        help='Pages to convert, e.g. "0,5-10,20".',
    ),
) -> None:
    """Convert a PDF file or arXiv URL to Markdown."""
    from my_ai_tools.pdf2md.converter import convert as do_convert

    input_as_path = Path(input_path)

    if input_as_path.is_dir():
        pdf_files = sorted(input_as_path.glob("*.pdf"))
        if not pdf_files:
            typer.echo(f"No PDF files found in {input_as_path}", err=True)
            raise typer.Exit(1)
        typer.echo(f"Found {len(pdf_files)} PDF(s) in {input_as_path}")
        for pdf in pdf_files:
            _convert_single(
                input_path=str(pdf),
                output_dir=output,
                backend=backend,
                use_llm=use_llm,
                llm_model=llm_model,
                llm_base_url=llm_base_url,
                force_ocr=force_ocr,
                page_range=page_range,
            )
    else:
        _convert_single(
            input_path=input_path,
            output_dir=output,
            backend=backend,
            use_llm=use_llm,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            force_ocr=force_ocr,
            page_range=page_range,
        )


def _convert_single(
    input_path: str,
    output_dir: Path | None,
    backend: str,
    use_llm: str | None,
    llm_model: str | None,
    llm_base_url: str | None,
    force_ocr: bool,
    page_range: str | None,
) -> None:
    """Convert a single PDF and write output files."""
    from my_ai_tools.pdf2md.converter import convert as do_convert

    typer.echo(f"Converting: {input_path}")
    typer.echo(f"  Backend: {backend}" + (f" + LLM ({use_llm})" if use_llm else ""))

    try:
        result = do_convert(
            input_path=input_path,
            output_dir=str(output_dir) if output_dir else None,
            backend=backend,
            use_llm=use_llm,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            force_ocr=force_ocr,
            page_range=page_range,
        )
    except NotImplementedError as e:
        typer.echo(f"  Error: {e}", err=True)
        raise typer.Exit(1)
    except (FileNotFoundError, ValueError, EnvironmentError) as e:
        typer.echo(f"  Error: {e}", err=True)
        raise typer.Exit(1)

    out_dir = output_dir or Path(input_path).parent
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(input_path).stem
    md_path = out_dir / f"{stem}.md"
    md_path.write_text(result.markdown, encoding="utf-8")
    typer.echo(f"  Markdown: {md_path}")

    if result.images:
        img_dir = out_dir / f"{stem}_images"
        img_dir.mkdir(exist_ok=True)
        for img_name, img_data in result.images.items():
            img_path = img_dir / img_name
            img_path.write_bytes(img_data)
        typer.echo(f"  Images: {img_dir}/ ({len(result.images)} files)")

    typer.echo("  Done.")


@app.command()
def backends() -> None:
    """List available backends and their installation status."""
    _check_backend("marker", "marker.converters.pdf", "pip install marker-pdf[full]")
    _check_backend("mineru", "magic_pdf", "pip install magic-pdf")


def _check_backend(name: str, module: str, install_cmd: str) -> None:
    try:
        __import__(module)
        typer.echo(f"  {name}: installed")
    except ImportError:
        typer.echo(f"  {name}: not installed (install with: {install_cmd})")


if __name__ == "__main__":
    app()
