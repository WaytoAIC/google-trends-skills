#!/usr/bin/env bash
set -euo pipefail

REPO="WaytoAIC/google-trends-skills"
REF="main"
TARGET="codex"
DEST=""

SKILLS=(
  "google-trends-hot-radar"
  "google-trends-keyword-watch"
)

usage() {
  cat <<'EOF'
Usage:
  install.sh [--target codex|openclaw] [--dest PATH] [--repo OWNER/REPO] [--ref REF]

Examples:
  bash install.sh
  bash install.sh --target codex
  bash install.sh --dest /tmp/google-trends-skills-smoke
  bash install.sh --repo WaytoAIC/google-trends-skills --ref v1.0.0
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --dest)
      DEST="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --ref)
      REF="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$DEST" ]]; then
  case "$TARGET" in
    codex)
      DEST="${CODEX_HOME:-$HOME/.codex}/skills"
      ;;
    openclaw)
      DEST="${OPENCLAW_HOME:-$HOME/.openclaw}/skills"
      ;;
    *)
      echo "--target must be codex or openclaw" >&2
      exit 1
      ;;
  esac
fi

SCRIPT_PATH="${BASH_SOURCE[0]:-${0:-}}"
if [[ -n "$SCRIPT_PATH" && -f "$SCRIPT_PATH" ]]; then
  SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)"
else
  SCRIPT_DIR=""
fi
TMP_DIR=""

cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

if [[ -n "$SCRIPT_DIR" && -d "$SCRIPT_DIR/google-trends-hot-radar" && -d "$SCRIPT_DIR/google-trends-keyword-watch" ]]; then
  SOURCE_DIR="$SCRIPT_DIR"
else
  TMP_DIR="$(mktemp -d)"
  ARCHIVE_URL="https://github.com/${REPO}/archive/${REF}.tar.gz"
  echo "Downloading ${ARCHIVE_URL}"
  curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR"
  SOURCE_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d -name '*google-trends-skills*' | head -n 1)"
  if [[ -z "$SOURCE_DIR" ]]; then
    SOURCE_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d | tail -n 1)"
  fi
fi

mkdir -p "$DEST"

for skill in "${SKILLS[@]}"; do
  if [[ ! -d "$SOURCE_DIR/$skill" ]]; then
    echo "Missing skill directory: $skill" >&2
    exit 1
  fi
  rm -rf "$DEST/$skill"
  cp -R "$SOURCE_DIR/$skill" "$DEST/$skill"
  echo "Installed $skill -> $DEST/$skill"
done

echo "Done. Installed ${#SKILLS[@]} Google Trends skills into $DEST"
