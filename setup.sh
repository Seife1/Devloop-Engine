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
  RELEASE_URL="https://github.com/Seife1/Devloop-Engine/releases/latest/download/$ASSET_NAME"
  if curl -fsSL "$RELEASE_URL" -o "$EXE_PATH"; then
    echo "  [OK] Downloaded $ASSET_NAME"
  else
    echo "  Notice: Release binary asset not yet built for $ASSET_NAME."
    echo -e "\033[33m  Falling back to direct Python/uv package engine...\033[0m"
    if command -v uv >/dev/null 2>&1; then
      uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force
      exit 0
    elif command -v pip3 >/dev/null 2>&1; then
      pip3 install --user "git+https://github.com/Seife1/Devloop-Engine.git"
      exit 0
    elif command -v pip >/dev/null 2>&1; then
      pip install --user "git+https://github.com/Seife1/Devloop-Engine.git"
      exit 0
    elif command -v python3 >/dev/null 2>&1; then
      python3 -m pip install --user "git+https://github.com/Seife1/Devloop-Engine.git"
      exit 0
    else
      echo -e "\033[36m  Bootstrapping ultra-fast standalone engine via uv...\033[0m"
      curl -LsSf https://astral.sh/uv/install.sh | sh
      export PATH="$HOME/.local/bin:$PATH"
      if command -v uv >/dev/null 2>&1; then
        uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force
        exit 0
      fi
      echo "  Error: Could not install binary or bootstrap environment."
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

echo -e "\033[36m[2/2] Verifying installation...\033[0m"
"$EXE_PATH" doctor

echo ""
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo -e "\033[32m  |                 INSTALLATION COMPLETE                       |\033[0m"
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo -e "\033[1;37m  * Executable:      $EXE_PATH\033[0m"
echo -e "\033[1;37m  * User PATH:       ~/.learnloop/bin permanently added\033[0m"
echo -e "\033[1;37m  * Privacy:         100% Local SQLite - Zero telemetry sent    \033[0m"
echo ""
echo -e "\033[36m  To initialize LearnLoop on any project, simply navigate to it:\033[0m"
echo -e "\033[1;37m      cd /path/to/your/project\033[0m"
echo -e "\033[33m      learnloop init\033[0m"
echo ""
echo -e "\033[36m  Available CLI commands inside initialized projects:\033[0m"
echo -e "\033[1;37m      learnloop briefing    # Session catch-up\033[0m"
echo -e "\033[1;37m      learnloop review      # Spaced repetition check\033[0m"
echo -e "\033[1;37m      learnloop concepts    # View concepts catalog\033[0m"
echo -e "\033[1;37m      learnloop dashboard   # Launch local web dashboard\033[0m"
echo -e "\033[1;37m      learnloop gui         # Launch native desktop window\033[0m"
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo ""
