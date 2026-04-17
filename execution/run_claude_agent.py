from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Claude Code non-interactively as a deterministic helper agent."
    )
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Inline prompt to send to Claude")
    prompt_group.add_argument("--prompt-file", help="Path to a UTF-8 text file containing the prompt")

    parser.add_argument("--output", help="Optional file path to write the model output")
    parser.add_argument(
        "--model",
        help="Optional Claude model alias or full model name, such as sonnet or claude-sonnet-4-6",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Claude CLI output format",
    )
    parser.add_argument(
        "--permission-mode",
        default="dontAsk",
        choices=("acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"),
        help="Permission mode passed through to Claude Code",
    )
    parser.add_argument(
        "--allowed-tool",
        action="append",
        dest="allowed_tools",
        default=[],
        help="Allowed tool entry to pass through to Claude Code. Repeat for multiple tools.",
    )
    parser.add_argument(
        "--append-system-prompt",
        help="Optional extra system guidance appended to Claude's default system prompt",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        help="Optional hard budget cap for the Claude run",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        help="Additional directories Claude may access. Repeat for multiple directories.",
    )
    return parser


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt
    return Path(args.prompt_file).read_text(encoding="utf-8")


def build_command(args: argparse.Namespace, prompt: str) -> list[str]:
    claude_executable = shutil.which("claude")
    if not claude_executable:
        claude_executable = shutil.which("claude.cmd")
    if not claude_executable:
        claude_executable = shutil.which("claude.ps1")
    if not claude_executable:
        raise FileNotFoundError("Claude Code CLI was not found on PATH.")

    command = [
        claude_executable,
        "--print",
        "--output-format",
        args.format,
        "--permission-mode",
        args.permission_mode,
        "--verbose",
    ]

    if args.model:
        command.extend(["--model", args.model])
    if args.append_system_prompt:
        command.extend(["--append-system-prompt", args.append_system_prompt])
    if args.max_budget_usd is not None:
        command.extend(["--max-budget-usd", str(args.max_budget_usd)])
    if args.allowed_tools:
        command.extend(["--allowedTools", *args.allowed_tools])
    for extra_dir in args.add_dir:
        command.extend(["--add-dir", extra_dir])

    command.append(prompt)
    return command


def write_output(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    prompt = load_prompt(args)
    command = build_command(args, prompt)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result.returncode

    stdout = result.stdout
    if args.output:
        write_output(Path(args.output), stdout)

    if args.format == "json":
        try:
            parsed = json.loads(stdout)
            sys.stdout.write(json.dumps(parsed, indent=2, ensure_ascii=True))
            sys.stdout.write("\n")
            return 0
        except json.JSONDecodeError:
            pass

    sys.stdout.write(stdout)
    if stdout and not stdout.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
