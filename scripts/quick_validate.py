#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:
    print(f"Missing PyYAML: {exc}", file=sys.stderr)
    sys.exit(1)


REQUIRED_SKILLS = [
    "google-trends-hot-radar",
    "google-trends-keyword-watch",
]


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print("Command failed:", " ".join(cmd), file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


def validate_skill(root, name):
    skill_dir = root / name
    if not skill_dir.is_dir():
        raise AssertionError(f"Missing skill directory: {name}")

    skill_md = skill_dir / "SKILL.md"
    config = skill_dir / "config.yaml"
    meta = skill_dir / "_meta.json"
    for path in [skill_md, config, meta]:
        if not path.exists():
            raise AssertionError(f"Missing required file: {path}")

    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise AssertionError(f"SKILL.md missing frontmatter: {skill_md}")
    if f"name: {name}" not in text:
        raise AssertionError(f"SKILL.md name mismatch: {skill_md}")

    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    if config_data["skill"]["name"] != name:
        raise AssertionError(f"config.yaml name mismatch: {config}")

    meta_data = json.loads(meta.read_text(encoding="utf-8"))
    if meta_data["slug"] != name:
        raise AssertionError(f"_meta.json slug mismatch: {meta}")


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    for name in REQUIRED_SKILLS:
        validate_skill(root, name)

    run(["bash", "-n", "google-trends-hot-radar/scripts/fetch-hot-trends.sh"], root)
    run(
        [
            sys.executable,
            "-m",
            "py_compile",
            "google-trends-keyword-watch/scripts/keyword-watch.py",
            "google-trends-keyword-watch/scripts/render-keyword-watch-html.py",
            "google-trends-hot-radar/scripts/fetch-trending-now.py",
            "google-trends-hot-radar/scripts/render-hot-radar-html.py",
            "scripts/render-google-trends-report.py",
        ],
        root,
    )
    for node_script in [
        "google-trends-keyword-watch/scripts/chrome-trends-fetch.mjs",
        "google-trends-keyword-watch/scripts/playwright-trends-fetch.mjs",
    ]:
        run(["node", "--check", node_script], root)
    run(["bash", "-n", "install.sh"], root)
    print("OK: Google Trends skills package validated")


if __name__ == "__main__":
    main()
