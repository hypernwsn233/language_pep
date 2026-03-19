#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# pep# Beta Installer for Linux / macOS
# After running this script:
#   source ~/.bashrc  (or restart terminal)
#   pep run examples/etl.pep
# ─────────────────────────────────────────────────────────────────────────────
set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT/.venv"
BIN_DIR="$HOME/.pep/bin"
WRAPPER="$BIN_DIR/pep"
PEP_VER="0.1.0-beta"

banner() {
  echo ""
  echo -e "  ${CYAN}pep# Language Installer  v${PEP_VER}${RESET}"
  echo -e "  ${BOLD}Pipeline-first. Parallel by default.${RESET}"
  echo ""
}

step()  { echo -e "  ${CYAN}>>  $*${RESET}"; }
ok()    { echo -e "  ${GREEN}ok  $*${RESET}"; }
fail()  { echo -e "  ${RED}!!  $*${RESET}"; exit 1; }

# ── Python ────────────────────────────────────────────────────────────────────
PYTHON=$(command -v python3 || command -v python || true)
[ -z "$PYTHON" ] && fail "Python 3.10+ not found. Install from https://python.org"
VER=$("$PYTHON" --version 2>&1)
ok "Python: $VER"

# ── Venv ──────────────────────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/python" ]; then
  step "Creating virtual environment"
  "$PYTHON" -m venv "$VENV_DIR"
else
  ok "Virtual environment exists"
fi

# ── Install package ───────────────────────────────────────────────────────────
step "Installing pep# package"
"$VENV_DIR/bin/pip" install -e "$ROOT" --quiet
ok "Package installed"

# ── Create wrapper ────────────────────────────────────────────────────────────
mkdir -p "$BIN_DIR"
cat > "$WRAPPER" <<EOF
#!/usr/bin/env sh
exec "$VENV_DIR/bin/python" -m pep_lang.cli "\$@"
EOF
chmod +x "$WRAPPER"
ok "Launcher: $WRAPPER"

# ── Shell profile ─────────────────────────────────────────────────────────────
PROFILE_LINE="export PATH=\"\$HOME/.pep/bin:\$PATH\""
ADDED=0
for f in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
  if [ -f "$f" ] && ! grep -q '.pep/bin' "$f" 2>/dev/null; then
    printf '\n# pep# language\n%s\n' "$PROFILE_LINE" >> "$f"
    ok "Added PATH to $f"
    ADDED=1
  fi
done
[ "$ADDED" -eq 0 ] && ok "PATH already configured"

# ── Logo ──────────────────────────────────────────────────────────────────────
if [ -f "$ROOT/tools/generate_logo.py" ]; then
  step "Generating logo.png"
  "$VENV_DIR/bin/python" "$ROOT/tools/generate_logo.py"
fi

echo ""
echo -e "  ${GREEN}${BOLD}pep# $PEP_VER installed!${RESET}"
echo ""
echo -e "  Restart your terminal, then:"
echo -e "  ${YELLOW}  pep run examples/etl.pep${RESET}"
echo -e "  ${YELLOW}  pep repl${RESET}"
echo ""
