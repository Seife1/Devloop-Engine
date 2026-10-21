#!/usr/bin/env bash
# LearnLoop One-Shot Universal Installer for macOS and Linux
# Usage: curl -fsSL https://learnloop.dev/setup.sh | bash
# Or run locally: ./setup.sh

set -euo pipefail

echo ""
echo -e "\033[36m  ================================================================\033[0m"
echo -e "\033[1;37m                LEARNLOOP - AI LEARNING COMPANION                 \033[0m"
echo -e "\033[90m              Zero Telemetry  *  100% Local-First                 \033[0m"
echo -e "\033[36m  ================================================================\033[0m"
echo ""

# Detect OS and Architecture
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$OS" in
  darwin)
    if [ "$ARCH" = "arm64" ]; then
      ASSET_NAME="learnloop-darwin-arm64"
    else
      ASSET_NAME="learnloop-darwin-x64"
    fi
    ;;
  linux)
    ASSET_NAME="learnloop-linux-x64"
    ;;
  *)
    echo "Unsupported OS: $OS"
    exit 1
    ;;
esac

BIN_DIR="$HOME/.learnloop/bin"
mkdir -p "$BIN_DIR"
EXE_PATH="$BIN_DIR/learnloop"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
LOCAL_DIST="$SCRIPT_DIR/dist/learnloop"

if [ -f "$LOCAL_DIST" ]; then
  echo -e "\033[33m[1/4] Using locally built binary from dist...\033[0m"
  cp "$LOCAL_DIST" "$EXE_PATH"
else
  echo -e "\033[36m[1/4] Downloading standalone binary for $OS ($ARCH)...\033[0m"
  RELEASE_URL="https://github.com/seife1/learnloop/releases/latest/download/$ASSET_NAME"
  if curl -fsSL "$RELEASE_URL" -o "$EXE_PATH"; then
    echo "  [OK] Downloaded $ASSET_NAME"
  else
    if [ ! -f "$EXE_PATH" ]; then
      echo "  Error: Failed to download release binary."
      exit 1
    fi
  fi
fi

chmod +x "$EXE_PATH"
echo -e "\033[32m  [OK] Installed executable to $EXE_PATH\033[0m"

# Add to PATH if missing
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    SHELL_PROFILE=""
    if [ -n "${ZSH_VERSION:-}" ] || [ -f "$HOME/.zshrc" ]; then
      SHELL_PROFILE="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
      SHELL_PROFILE="$HOME/.bashrc"
    elif [ -f "$HOME/.profile" ]; then
      SHELL_PROFILE="$HOME/.profile"
    fi

    if [ -n "$SHELL_PROFILE" ]; then
      if ! grep -q "$BIN_DIR" "$SHELL_PROFILE" 2>/dev/null; then
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_PROFILE"
        echo -e "\033[32m  [OK] Added ~/.learnloop/bin to $SHELL_PROFILE\033[0m"
      fi
    fi
    export PATH="$PATH:$BIN_DIR"
    ;;
esac

echo -e "\033[36m[2/4] Initializing LearnLoop & local SQLite database...\033[0m"
"$EXE_PATH" init --integrate

echo -e "\033[36m[3/4] Ingesting AI Companion rules into current project...\033[0m"
echo -e "\033[32m  [OK] AGENTS.md, .cursorrules & .windsurfrules ready\033[0m"

echo -e "\033[36m[4/4] Verification check...\033[0m"
"$EXE_PATH" doctor

echo ""
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo -e "\033[32m  |                 INSTALLATION COMPLETE                       |\033[0m"
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo -e "\033[1;37m  * IDEs Configured: Cursor, VS Code, Windsurf, Claude, Zed\033[0m"
echo -e "\033[1;37m  * Git Tracking:    Automatic via non-blocking post-commit hook\033[0m"
echo -e "\033[1;37m  * Privacy:         100% Local SQLite - Zero telemetry sent    \033[0m"
echo -e "\033[36m  * Dashboard:       Run 'learnloop dashboard' to launch UI     \033[0m"
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo ""
