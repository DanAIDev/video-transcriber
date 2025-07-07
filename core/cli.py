"""Command-line interface for the video-transcriber package.

Example usage
-------------
$ python -m core.cli submit path/to/file.mp4
$ python -m core.cli batch  path/to/dir   --language de-DE
$ python -m core.cli poll  # continue polling unfinished jobs

The CLI is intentionally thin; all heavy lifting lives in ``core.pipeline``.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.pipeline import TranscriptionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
load_dotenv()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("video-transcriber")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="submit a single file")
    submit.add_argument("media", type=Path)
    submit.add_argument("--language", default="en-US")

    batch = sub.add_parser("batch", help="submit all media in directory")
    batch.add_argument("directory", type=Path)
    batch.add_argument("--language", default="en-US")

    poll = sub.add_parser("poll", help="poll unfinished jobs until done")
    poll.add_argument("--interval", type=int, default=30)

    return parser


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    args = _build_parser().parse_args(argv)

    pipeline = TranscriptionPipeline()

    if args.command == "submit":
        pipeline.submit_single(args.media, language=args.language)
    elif args.command == "batch":
        pipeline.submit_batch(args.directory, language=args.language)
    elif args.command == "poll":
        pipeline.poll(interval_sec=args.interval)
    else:
        raise SystemExit(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
