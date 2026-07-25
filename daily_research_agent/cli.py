from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .pipeline import ResearchPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="daily-research-agent",
        description="Collect, rank, and summarize recent robotics research.",
    )
    parser.add_argument(
        "--config",
        default="config.example.json",
        help="Path to a JSON config file.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Override the lookback window in days.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override the maximum number of papers in the report.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate a report without updating the local paper history.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)

    if args.days is not None:
        config["agent"]["lookback_days"] = args.days
    if args.limit is not None:
        config["agent"]["max_report_items"] = args.limit

    pipeline = ResearchPipeline(config=config, root=config_path.parent.resolve())
    result = pipeline.run(dry_run=args.dry_run)

    print(f"Collected: {result.collected_count}")
    print(f"After dedupe: {result.unique_count}")
    print(f"Selected: {result.selected_count}")
    print(f"Report: {result.report_path}")

