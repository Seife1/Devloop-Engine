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
      # Linux ARM64 (aarch64) or other architecture: pre-built binaries are x86_64; route to Python/uv
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
  echo -e "\033[33m[1/4] Using locally built binary from dist...\033[0m"
  cp "$LOCAL_DIST" "$EXE_PATH"
  INSTALL_SUCCESS=true
elif [ "$DOWNLOAD_BINARY" = true ]; then
  echo -e "\033[36m[1/4] Downloading standalone binary for $OS ($ARCH)...\033[0m"
  RELEASE_URL="https://github.com/Seife1/Devloop-Engine/releases/latest/download/$ASSET_NAME"
  if curl -fsSL "$RELEASE_URL" -o "$EXE_PATH"; then
    echo "  [OK] Downloaded $ASSET_NAME"
    INSTALL_SUCCESS=true
  else
    echo "  Notice: Release binary asset not yet reachable for $ASSET_NAME."
  fi
fi

if [ "$INSTALL_SUCCESS" = false ]; then
  echo -e "\033[33m  Falling back to direct Python/uv package engine...\033[0m"

  # 1. Primary: If uv is already installed, use it
  if command -v uv >/dev/null 2>&1; then
    if uv tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force; then
      INSTALL_SUCCESS=true
    fi
  fi

  # 2. Secondary: Bootstrap uv (zero dependencies, works on any modern Linux/macOS)
  if [ "$INSTALL_SUCCESS" = false ]; then
    echo -e "\033[36m  Bootstrapping ultra-fast standalone engine via uv...\033[0m"
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
      UV_BIN="$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
      if [ -x "$UV_BIN" ]; then
        if "$UV_BIN" tool install "git+https://github.com/Seife1/Devloop-Engine.git" --force; then
          INSTALL_SUCCESS=true
        fi
      fi
    fi
  fi

  # 3. Tertiary: Fallback to pipx / pip3 / pip only if uv bootstrap failed
  if [ "$INSTALL_SUCCESS" = false ]; then
    if command -v pipx >/dev/null 2>&1; then
      if pipx install "git+https://github.com/Seife1/Devloop-Engine.git"; then
        INSTALL_SUCCESS=true
      fi
    elif command -v pip3 >/dev/null 2>&1; then
      if pip3 install --user "git+https://github.com/Seife1/Devloop-Engine.git" 2>/dev/null || pip3 install --user --break-system-packages "git+https://github.com/Seife1/Devloop-Engine.git"; then
        INSTALL_SUCCESS=true
      fi
    elif python3 -m pip --version >/dev/null 2>&1; then
      if python3 -m pip install --user "git+https://github.com/Seife1/Devloop-Engine.git" 2>/dev/null || python3 -m pip install --user --break-system-packages "git+https://github.com/Seife1/Devloop-Engine.git"; then
        INSTALL_SUCCESS=true
      fi
    fi
  fi

  if [ "$INSTALL_SUCCESS" = false ]; then
    echo "  Error: Could not install binary or bootstrap environment."
    exit 1
  fi

  # Link or copy installed Python/uv binary to $EXE_PATH
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

# macOS Gatekeeper and Code Signing safeguards
if [ "$OS" = "darwin" ]; then
  xattr -d com.apple.quarantine "$EXE_PATH" 2>/dev/null || true
  codesign -s - "$EXE_PATH" 2>/dev/null || true
fi

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
