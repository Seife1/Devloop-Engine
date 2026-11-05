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

DOWNLOAD_BINARY=true
ASSET_NAME=""

case "$OS" in
  darwin)
    if [ "$ARCH" = "arm64" ]; then
      ASSET_NAME="learnloop-darwin-arm64"
    else
      ASSET_NAME="learnloop-darwin-x64"
    fi
    ;;
  linux)
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
      ASSET_NAME="learnloop-linux-x64"
    else
      DOWNLOAD_BINARY=false
    fi
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

INSTALL_SUCCESS=false

if [ -f "$LOCAL_DIST" ]; then
  echo -e "\033[36m[1/3] Using locally built binary from dist...\033[0m"
  cp "$LOCAL_DIST" "$EXE_PATH"
  INSTALL_SUCCESS=true
elif [ "$DOWNLOAD_BINARY" = true ]; then
  echo -e "\033[36m[1/3] Downloading standalone binary for $OS ($ARCH)...\033[0m"
  RELEASE_URL="https://github.com/Seife1/Devloop-Engine/releases/latest/download/$ASSET_NAME"
  if curl -fsSL "$RELEASE_URL" -o "$EXE_PATH" 2>/dev/null; then
    echo -e "\033[32m      ✓ Downloaded $ASSET_NAME\033[0m"
    INSTALL_SUCCESS=true
  fi
fi

if [ "$INSTALL_SUCCESS" = false ]; then
  echo -e "\033[36m[1/3] Setting up environment...\033[0m"
  if ! command -v uv >/dev/null 2>&1; then
    echo -e "      • Bootstrapping standalone package engine (uv)..."
    curl -LsSf https://astral.sh/uv/install.sh 2>/dev/null | env CARGO_DIST_FORCE_INSTALL=true sh >/dev/null 2>&1 || true
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  fi

  UV_BIN="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
  if [ -x "$UV_BIN" ]; then
    echo -e "\033[36m[2/3] Installing LearnLoop engine (fetching packages, ~15s)...\033[0m"
    if "$UV_BIN" tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force --quiet 2>/dev/null; then
      INSTALL_SUCCESS=true
      echo -e "\033[32m      ✓ LearnLoop installed successfully\033[0m"
    fi
  fi

  if [ "$INSTALL_SUCCESS" = false ]; then
    echo -e "\033[36m[2/3] Installing LearnLoop via package fallback...\033[0m"
    if command -v pipx >/dev/null 2>&1; then
      pipx install "git+https://github.com/Seife1/Devloop-Engine.git" --quiet 2>/dev/null && INSTALL_SUCCESS=true
    elif command -v pip3 >/dev/null 2>&1; then
      (pip3 install --user "git+https://github.com/Seife1/Devloop-Engine.git" --quiet 2>/dev/null || pip3 install --user --break-system-packages "git+https://github.com/Seife1/Devloop-Engine.git" --quiet 2>/dev/null) && INSTALL_SUCCESS=true
    elif python3 -m pip --version >/dev/null 2>&1; then
      (python3 -m pip install --user "git+https://github.com/Seife1/Devloop-Engine.git" --quiet 2>/dev/null || python3 -m pip install --user --break-system-packages "git+https://github.com/Seife1/Devloop-Engine.git" --quiet 2>/dev/null) && INSTALL_SUCCESS=true
    fi
  fi

  if [ "$INSTALL_SUCCESS" = false ]; then
    echo -e "\033[31m  Error: Installation failed. Please ensure git and internet access are available.\033[0m"
    exit 1
  fi

  # Resolve target binary
  RESOLVED_BIN="$(command -v learnloop 2>/dev/null || true)"
  if [ -z "$RESOLVED_BIN" ]; then
    for candidate in "$HOME/.local/bin/learnloop" "$HOME/Library/Python/3.*/bin/learnloop"; do
      for c in $candidate; do
        if [ -f "$c" ]; then
          RESOLVED_BIN="$c"
          break 2
        fi
      done
    done
  fi

  if [ -n "$RESOLVED_BIN" ] && [ -f "$RESOLVED_BIN" ]; then
    cp "$RESOLVED_BIN" "$EXE_PATH"
  fi
fi

chmod +x "$EXE_PATH"

if [ "$OS" = "darwin" ]; then
  xattr -d com.apple.quarantine "$EXE_PATH" 2>/dev/null || true
  codesign -s - "$EXE_PATH" 2>/dev/null || true
fi

# Add to PATH in all relevant shell profiles
PROFILE_UPDATED=false
for profile in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
  if [ -f "$profile" ]; then
    PROFILE_UPDATED=true
    if ! grep -q "$BIN_DIR" "$profile" 2>/dev/null; then
      echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$profile"
    fi
  fi
done

if [ "$PROFILE_UPDATED" = false ]; then
  echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.profile"
fi

echo -e "\033[36m[3/3] Verifying installation & local database...\033[0m"
DOCTOR_OUT="$("$EXE_PATH" doctor 2>&1)" || true
if echo "$DOCTOR_OUT" | grep -q "ok"; then
  echo -e "\033[32m      ✓ Doctor check passed (local SQLite engine ready)\033[0m"
else
  echo "$DOCTOR_OUT"
fi

echo ""
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo -e "\033[32m  |                 INSTALLATION COMPLETE                       |\033[0m"
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo -e "\033[1;37m  * Executable:      $EXE_PATH\033[0m"
echo -e "\033[1;37m  * User PATH:       ~/.learnloop/bin permanently added\033[0m"
echo -e "\033[1;37m  * Privacy:         100% Local SQLite - Zero telemetry sent    \033[0m"
echo ""

echo -e "\033[1;33m  QUICK START FOR NEW USERS:\033[0m"
echo ""
echo -e "\033[36m  1. Verify engine & database:\033[0m"
echo -e "\033[1;37m     learnloop doctor\033[0m"
echo ""
echo -e "\033[36m  2. Connect to any project (Ghost Mode - 0 repo pollution):\033[0m"
echo -e "\033[1;37m     cd /path/to/your/project\033[0m"
echo -e "\033[33m     learnloop init\033[0m"
echo ""
echo -e "\033[36m  3. Open local learning dashboard:\033[0m"
echo -e "\033[1;37m     learnloop dashboard   (or: learnloop gui)\033[0m"
echo ""
echo -e "\033[90m  * In active projects: run 'learnloop briefing' or '/review' in IDE chat\033[0m"
echo -e "\033[90m  * Full command list:  learnloop --help\033[0m"
echo -e "\033[90m  * Clean uninstaller:  learnloop uninstall\033[0m"
echo -e "\033[32m  +-------------------------------------------------------------+\033[0m"
echo ""
