from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cmd(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--file", default=str(ROOT / "data" / "digest" / "latest.md"))
    args = ap.parse_args()

    title = f"Daily AI Digest - {args.date}"
    body = Path(args.file).read_text(encoding="utf-8")

    existing = run_cmd(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            args.repo,
            "--search",
            f'in:title "{title}"',
            "--json",
            "number,title",
            "--limit",
            "1",
        ]
    )

    if existing and existing != "[]":
        issue_num = run_cmd(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                args.repo,
                "--search",
                f'in:title "{title}"',
                "--json",
                "number",
                "--jq",
                ".[0].number",
                "--limit",
                "1",
            ]
        )
        run_cmd(["gh", "issue", "edit", issue_num, "--repo", args.repo, "--title", title, "--body", body])
        print(f"updated_issue=#{issue_num}")
    else:
        url = run_cmd(["gh", "issue", "create", "--repo", args.repo, "--title", title, "--body", body])
        print(f"created_issue={url}")


if __name__ == "__main__":
    main()
