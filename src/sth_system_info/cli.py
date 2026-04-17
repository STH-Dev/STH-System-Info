from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .collector import collect_host, resolve_password
from .config import load_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect SPEC-style system information from remote Linux hosts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect system information from one configured host.")
    collect_parser.add_argument("--config", type=Path, required=True, help="Path to the TOML host configuration.")
    collect_parser.add_argument("--host", required=True, help="Host name from the configuration.")
    collect_parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("runs"),
        help="Root output directory for timestamped collections.",
    )
    collect_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Explicit output directory. Overrides the timestamped output-root layout.",
    )
    collect_parser.add_argument("--password", default=None, help="SSH password. Prefer env vars instead.")
    collect_parser.add_argument(
        "--password-env",
        default=None,
        help="Environment variable holding the SSH password. Defaults to STH_SYSTEM_INFO_SSH_PASSWORD or STH_LATENCY_SSH_PASSWORD.",
    )
    return parser


def collect_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    host = config.require_host(args.host)
    password = resolve_password(args.password, args.password_env)
    artifacts = collect_host(
        host=host,
        password=password,
        output_root=args.output_root,
        output_dir=args.output_dir,
    )
    print(f"Output directory: {artifacts.output_dir}")
    print(f"Summary: {artifacts.summary_path}")
    print(f"Profile: {artifacts.profile_path}")
    print(f"Manifest: {artifacts.manifest_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "collect":
        return collect_command(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
