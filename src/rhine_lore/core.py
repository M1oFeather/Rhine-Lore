"""Application startup orchestration."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from rhine_lore.server import serve


def build_parser() -> argparse.ArgumentParser:
    default_web_root = Path(__file__).resolve().parents[2] / "ui" / "dist"
    if not default_web_root.exists():
        default_web_root = Path(__file__).resolve().parents[2] / "web"
    parser = argparse.ArgumentParser(description="Run the Rhine-Lore local workspace.")
    parser.add_argument(
        "--host",
        default=os.environ.get("RHINE_LORE_HOST", "0.0.0.0"),
        help="Host interface to bind; 0.0.0.0 opens the site to the local network.",
    )
    parser.add_argument("--port", default=8786, type=int, help="Port to bind.")
    parser.add_argument(
        "--web-root",
        default=str(default_web_root),
        help="Static web root.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    serve(host=args.host, port=args.port, web_root=Path(args.web_root))
