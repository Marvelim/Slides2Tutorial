"""Command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .client import OpenAICompatibleNotesClient
from .generator import TutorialConfig, TutorialGenerator

DEFAULT_MODEL = "gemini-3.1-pro"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slides2tutorial",
        description="Generate Chinese Markdown + LaTeX notes from a PDF via an OpenAI-compatible Gemini endpoint.",
    )
    parser.add_argument("pdf", type=Path, help="Input PDF path.")
    parser.add_argument("--base-url", help="OpenAI-compatible API base URL.")
    parser.add_argument("--api-key", help="API key for the OpenAI-compatible endpoint.")
    parser.add_argument("--model", help=f"Model name. Defaults to {DEFAULT_MODEL}.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/tutorial.md"),
        help="Output Markdown path. Defaults to output/tutorial.md.",
    )
    parser.add_argument(
        "--state",
        type=Path,
        help="JSONL state path. Defaults to <out directory>/state.jsonl.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=180,
        help="PDF screenshot DPI. Defaults to 180.",
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        help="Only process the first N pages.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore existing state and regenerate pages from the beginning.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    parser = build_parser()
    args = parser.parse_args(argv)

    base_url = args.base_url or os.getenv("GEMINI_BASE_URL")
    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    model = args.model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    state_path = args.state or args.out.parent / "state.jsonl"

    if not base_url:
        print("Error: missing --base-url or GEMINI_BASE_URL.", file=sys.stderr)
        return 1
    if not api_key:
        print("Error: missing --api-key or GEMINI_API_KEY.", file=sys.stderr)
        return 1

    config = TutorialConfig(
        pdf_path=args.pdf,
        output_path=args.out,
        state_path=state_path,
        model=model,
        dpi=args.dpi,
        limit_pages=args.limit_pages,
        force=args.force,
    )

    try:
        client = OpenAICompatibleNotesClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        result = TutorialGenerator(
            config=config,
            client=client,
            progress=lambda message: print(message, file=sys.stderr),
        ).run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        "Done: "
        f"{result.generated_pages} generated, "
        f"{result.skipped_pages} skipped, "
        f"{result.total_pages} total pages."
    )
    print(f"Markdown: {result.output_path}")
    print(f"State: {result.state_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
