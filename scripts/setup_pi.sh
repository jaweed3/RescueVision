#!/usr/bin/env bash
# =============================================================================
# RescueVision Edge — Raspberry Pi 4 Setup Script  v1.0
# =============================================================================
# Installs everything needed to run RescueVision on Raspberry Pi 4 (ARM64).
# Designed with maximum robustness: every failure is caught, explained, and
# offers recovery paths. The script is fully idempotent — safe to re-run.
#
# Usage:
#   chmod +x scripts/setup_pi.sh
#   sudo ./scripts/setup_pi.sh
#
# Options:
#   --skip-system-update   Skip apt update/upgrade (faster re-runs)
#   --skip-swap            Skip swap file creation
#   --skip-nginx           Skip Nginx setup (use Vite dev server instead)
#   --pi-user <user>       Linux user to own services (default: pi)
#   --model-path <path>    Path to model.onnx file to copy into project
#   --help                 Show this help
# =============================================================================

set -uo pipefail

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
SKIP_SYSTEM_UPDATE=false
SKIP_SWAP=false
SKIP_NGINX=false
PI_USER="pi"
CUSTOM_MODEL_PATH=""
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_FILE="/tmp/rescuevision-setup-$(date +%Y%m%d-%H%M%S).log"
FAILED_STEPS=()

# ──────────────────────────────────────────────────────────────────────────────
# Color output
# ──────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }
log_step()  { echo -e "\n${CYAN}━━━ $* ━━━${NC}" | tee -a "$LOG_FILE"; }
log_debug() { echo -e "${GRAY}[DEBUG]${NC} $*" >> "$LOG_FILE"; }

# ──────────────────────────────────────────────────────────────────────────────
# Robust step runner: catches failures, logs them, tracks them, never exits
# ──────────────────────────────────────────────────────────────────────────────
run_step() {
    local step_name="$1"
    local func="$2"
    shift 2

    echo ""
    echo -e "${CYAN}━━━ [${step_name}] ━━━${NC}"
    echo -e "${GRAY}→ ${func} $*${NC}"

    if "$func" "$@" 2>>"$LOG_FILE"; then
        echo -e "${GREEN}  ✓ ${step_name} passed${NC}"
    else
        local exit_code=$?
        echo -e "${RED}  ✗ ${step_name} FAILED (exit code: ${exit_code})${NC}"
        FAILED_STEPS+=("${step_name}")
        log_error "Step '${step_name}' failed with exit code ${exit_code}"
        log_error "See details: tail -50 ${LOG_FILE}"
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# Helper: retry a command up to N times
# ──────────────────────────────────────────────────────────────────────────────
retry() {
    local max_attempts="$1"
    local cmd="$2"
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if eval "$cmd" 2>>"$LOG_FILE"; then
            return 0
        fi
        log_warn "  (attempt ${attempt}/${max_attempts}) failed, retrying in ${attempt}s..."
        sleep "$attempt"
        attempt=$((attempt + 1))
    done

    log_error "  All ${max_attempts} attempts failed."
    return 1
}

# ──────────────────────────────────────────────────────────────────────────────
# Helper: check if a command exists
# ──────────────────────────────────────────────────────────────────────────────
cmd_exists() {
    command -v "$1" &>/dev/null
}

# ──────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ──────────────────────────────────────────────────────────────────────────────
usage() {
    sed -n '3,20p' "$0"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-system-update) SKIP_SYSTEM_UPDATE=true; shift ;;
        --skip-swap)          SKIP_SWAP=true; shift ;;
        --skip-nginx)         SKIP_NGINX=true; shift ;;
        --pi-user)            PI_USER="$2"; shift 2 ;;
        --model-path)         CUSTOM_MODEL_PATH="$2"; shift 2 ;;
        --help)               usage ;;
        *)                    log_error "Unknown option: $1"; usage ;;
    esac
done

# =============================================================================
# STEP 1: Pre-flight checks
# =============================================================================
step_preflight() {
    log_debug "Starting preflight checks..."

    # Must be root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (sudo)."
        log_error "Re-run with: sudo ./scripts/setup_pi.sh"
        return 1
    fi

    # Architecture check (non-fatal warning on non-ARM64)
    local arch
    arch=$(uname -m)
    case "$arch" in
        aarch64)  log_ok "Architecture: aarch64 (ARM64) ✓" ;;
        armv7l|armv6l)
            log_warn "Architecture: $arch (32-bit ARM). ONNX Runtime may not work."
            log_warn "Consider using a 64-bit OS on your Pi 4."
            ;;
        *)
            log_warn "Architecture: $arch (not ARM). Targeting Raspberry Pi, but continuing."
            ;;
    esac

    # Verify project structure
    local missing_dirs=()
    [[ -d "$BACKEND_DIR" ]] || missing_dirs+=("$BACKEND_DIR")
    [[ -d "$FRONTEND_DIR" ]] || missing_dirs+=("$FRONTEND_DIR")

    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        log_error "Project directories missing: ${missing_dirs[*]}"
        log_error "Run this script from the RescueVision project root."
        log_error "Expected structure: PROJECT/backend/ and PROJECT/frontend/"
        return 1
    fi
    log_ok "Project structure: ${PROJECT_DIR}"

    # Memory check
    if [[ -f /proc/meminfo ]]; then
        local total_mem_mb
        total_mem_mb=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null)
        log_info "RAM: ${total_mem_mb} MB"
        if [[ ${total_mem_mb:-0} -lt 1500 ]]; then
            log_warn "Less than 1.5 GB RAM. Consider a 4 GB Pi 4 for smooth operation."
        fi
    else
        log_warn "Cannot check memory (/proc/meminfo not available). Continuing..."
    fi

    # Disk space check
    if command -v df &>/dev/null; then
        local avail_mb
        avail_mb=$(df -m "$PROJECT_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
        if [[ -n "$avail_mb" && "$avail_mb" -lt 1500 ]]; then
            log_error "Insufficient disk: ~${avail_mb} MB free. Need ~1.5 GB."
            log_error "Free up space: sudo apt-get clean && sudo journalctl --vacuum-size=100M"
            return 1
        fi
        log_ok "Disk: ~${avail_mb} MB free"
    fi

    # OS detection
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release 2>/dev/null || true
        log_info "OS: ${PRETTY_NAME:-unknown}"
    fi

    # Python check
    if cmd_exists python3; then
        local pyver
        pyver=$(python3 --version 2>&1)
        log_info "System Python: ${pyver}"
        local pymajor pyminor
        pymajor=$(python3 -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
        pyminor=$(python3 -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)
        if [[ "${pymajor:-0}" -lt 3 || ( "${pymajor:-0}" -eq 3 && "${pyminor:-0}" -lt 9 ) ]]; then
            log_warn "Python >= 3.9 recommended. Found: ${pymajor}.${pyminor}"
        fi
    else
        log_warn "python3 not found — will be installed by system packages step."
    fi

    return 0
}

# =============================================================================
# STEP 2: System packages
# =============================================================================
step_system_packages() {
    log_debug "Starting system package installation..."

    # Update
    if [[ "$SKIP_SYSTEM_UPDATE" == false ]]; then
        log_info "Updating package lists..."
        if ! retry 3 "apt-get update -y"; then
            log_error "apt-get update failed. Check network connectivity."
            log_error "If offline, re-run with: --skip-system-update"
            return 1
        fi

        log_info "Upgrading packages (this may take a while)..."
        apt-get upgrade -y -o Dpkg::Options::="--force-confnew" 2>>"$LOG_FILE" || log_warn "Some packages couldn't be upgraded (non-fatal)"
    else
        log_info "Skipping system update/upgrade"
    fi

    # Install packages in groups so one failure doesn't kill everything
    local essential_pkgs=(
        python3 python3-pip python3-venv python3-dev
        git curl wget ca-certificates gnupg
    )
    local opencv_pkgs=(
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
    )
    local build_pkgs=(
        build-essential cmake pkg-config
    )
    local utils_pkgs=(
        libv4l-dev v4l-utils
    )
    local nginx_pkg=()
    if [[ "$SKIP_NGINX" == false ]]; then
        nginx_pkg=(nginx)
    fi

    local all_pkgs=(
        "${essential_pkgs[@]}"
        "${opencv_pkgs[@]}"
        "${build_pkgs[@]}"
        "${utils_pkgs[@]}"
        "${nginx_pkg[@]}"
    )

    log_info "Installing packages: ${all_pkgs[*]}"
    if ! retry 3 "apt-get install -y ${all_pkgs[*]}"; then
        # Try without optional packages
        log_warn "Full package install failed. Retrying with essential only..."
        if ! retry 3 "apt-get install -y ${essential_pkgs[*]}"; then
            log_error "Even essential packages failed to install. Check apt sources."
            return 1
        fi
        # Try OpenCV separately (often the culprit)
        log_info "Trying OpenCV packages separately..."
        apt-get install -y "${opencv_pkgs[@]}" 2>>"$LOG_FILE" || log_warn "Some OpenCV packages unavailable (using opencv-python-headless as fallback)"
    fi

    # Node.js via NodeSource (only if not present or too old)
    if cmd_exists node; then
        local node_major
        node_major=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
        if [[ -n "$node_major" && "$node_major" -ge 18 ]]; then
            log_ok "Node.js v$(node --version) already installed"
        else
            log_info "Node.js $(node --version 2>/dev/null || echo 'unknown') is too old. Upgrading to 18.x..."
            install_nodejs || return 1
        fi
    else
        log_info "Installing Node.js 18.x..."
        install_nodejs || return 1
    fi

    return 0
}

install_nodejs() {
    # Try NodeSource first
    if curl -fsSL https://deb.nodesource.com/setup_18.x -o /tmp/nodesource_setup.sh 2>>"$LOG_FILE"; then
        bash /tmp/nodesource_setup.sh 2>>"$LOG_FILE" || true
        apt-get install -y nodejs 2>>"$LOG_FILE" || {
            log_warn "NodeSource install failed, trying Debian/Ubuntu repo..."
            apt-get install -y nodejs npm 2>>"$LOG_FILE" || {
                log_warn "System nodejs too old. Install Node.js 18+ manually: https://nodejs.org"
                return 1
            }
        }
    else
        log_warn "Cannot reach NodeSource (offline?). Trying system packages..."
        apt-get install -y nodejs npm 2>>"$LOG_FILE" || {
            log_warn "Node.js not available via apt. Install manually: https://nodejs.org"
            return 1
        }
    fi
    log_ok "Node.js $(node --version) installed"
    return 0
}

# =============================================================================
# STEP 3: Swap configuration
# =============================================================================
step_swap() {
    if [[ "$SKIP_SWAP" == true ]]; then
        log_info "Skipping swap configuration"
        return 0
    fi

    # Only proceed if /proc/meminfo exists
    if [[ ! -f /proc/meminfo ]]; then
        log_warn "Cannot check memory. Skipping swap config."
        return 0
    fi

    local total_mem_mb
    total_mem_mb=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null)
    local desired_total=4096
    local swap_needed=$((desired_total - total_mem_mb))

    if [[ $swap_needed -le 0 ]]; then
        log_ok "RAM (${total_mem_mb} MB) ≥ ${desired_total} MB — swap not needed"
        return 0
    fi

    # Check existing swap
    local current_swap
    current_swap=$(awk '/SwapTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null)

    if [[ ${current_swap:-0} -ge $swap_needed ]]; then
        log_ok "Existing swap (${current_swap} MB) is sufficient"
        return 0
    fi

    local swap_file="/swapfile"
    local add_mb=$((swap_needed - current_swap))

    log_info "Adding ${add_mb} MB swap to reach ${desired_total} MB total..."

    # Disable dphys-swapfile if present (Raspberry Pi OS default)
    if systemctl is-active --quiet dphys-swapfile 2>/dev/null; then
        systemctl stop dphys-swapfile 2>/dev/null || true
        systemctl disable dphys-swapfile 2>/dev/null || true
    fi

    # Remove old swapfile if it exists from a previous run
    if [[ -f "$swap_file" ]]; then
        swapoff "$swap_file" 2>/dev/null || true
        rm -f "$swap_file"
    fi

    # Create swap — fallocate first, fall back to dd
    if ! fallocate -l "${add_mb}M" "$swap_file" 2>/dev/null; then
        log_info "fallocate unavailable, using dd (may take a minute)..."
        dd if=/dev/zero of="$swap_file" bs=1M count="$add_mb" status=progress 2>>"$LOG_FILE"
    fi

    chmod 600 "$swap_file"
    mkswap "$swap_file" 2>>"$LOG_FILE" || {
        log_error "Failed to create swap filesystem"
        rm -f "$swap_file"
        return 1
    }
    swapon "$swap_file" 2>>"$LOG_FILE" || {
        log_error "Failed to enable swap"
        return 1
    }

    # Persist in fstab (avoid duplicates)
    if ! grep -q "$swap_file" /etc/fstab 2>/dev/null; then
        echo "$swap_file none swap sw 0 0" >> /etc/fstab
    fi

    # Set swappiness
    sysctl vm.swappiness=10 2>/dev/null || true
    echo "vm.swappiness=10" > /etc/sysctl.d/99-swap.conf 2>/dev/null || true

    local new_total=$((total_mem_mb + add_mb + (current_swap)))
    log_ok "Swap: +${add_mb} MB (total RAM+swap ≈ ${new_total} MB)"
    return 0
}

# =============================================================================
# STEP 4: Python virtual environment + dependencies
# =============================================================================
step_python_env() {
    log_debug "Starting Python env setup..."

    # Create venv if needed
    if [[ -d "$VENV_DIR" ]]; then
        if "$VENV_DIR/bin/python" --version &>/dev/null; then
            log_info "venv exists and works: $VENV_DIR"
        else
            log_warn "Existing venv is broken. Recreating..."
            rm -rf "$VENV_DIR"
            python3 -m venv "$VENV_DIR" 2>>"$LOG_FILE" || {
                log_error "Failed to create venv. Is python3-venv installed?"
                return 1
            }
        fi
    else
        python3 -m venv "$VENV_DIR" 2>>"$LOG_FILE" || {
            log_error "Failed to create virtual environment."
            log_error "Try: sudo apt-get install python3-venv"
            return 1
        }
        log_ok "venv created at ${VENV_DIR}"
    fi

    # Upgrade pip
    log_info "Upgrading pip..."
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel 2>>"$LOG_FILE" || log_warn "pip upgrade failed (non-critical)"

    # ─── Install ONNX Runtime ──────────────────────────────────────────────
    local arch
    arch=$(uname -m)
    local onnx_ok=false

    log_info "Installing ONNX Runtime..."
    if [[ "$arch" == "aarch64" ]]; then
        # ARM64 strategy: try multiple approaches in order
        # 1. Try latest compatible onnxruntime (≥1.17 has aarch64 wheels)
        # 2. Try onnxruntime-silicon (community build)
        # 3. Build from source (last resort)
        if "$VENV_DIR/bin/pip" install "onnxruntime>=1.17.0,<1.19.0" 2>>"$LOG_FILE"; then
            onnx_ok=true
        else
            log_warn "onnxruntime (PyPI) download failed. Trying alternative..."
            # Try without version pin
            if "$VENV_DIR/bin/pip" install onnxruntime 2>>"$LOG_FILE"; then
                onnx_ok=true
            else
                log_warn "Standard onnxruntime failed. Trying onnxruntime-silicon..."
                # Try onnxruntime-silicon (community ARM build)
                if "$VENV_DIR/bin/pip" install onnxruntime-silicon 2>>"$LOG_FILE"; then
                    onnx_ok=true
                else
                    log_warn "All binary options failed. Building ONNX from source (may take 30+ min)..."
                    log_warn "Consider pre-installing onnxruntime via:"
                    log_warn "  pip install onnxruntime --only-binary :all:"
                    log_info "Attempting source build..."
                    if "$VENV_DIR/bin/pip" install onnxruntime --no-binary onnxruntime 2>>"$LOG_FILE"; then
                        onnx_ok=true
                    else
                        log_warn "ONNX Runtime source build also failed."
                        log_warn "The backend will still install, but inference needs onnxruntime."
                        log_warn "Pre-built wheels: https://github.com/nknytc/onnxruntime-silicon/releases"
                    fi
                fi
            fi
        fi
    else
        if "$VENV_DIR/bin/pip" install "onnxruntime>=1.17.0,<1.19.0" 2>>"$LOG_FILE"; then
            onnx_ok=true
        else
            "$VENV_DIR/bin/pip" install onnxruntime 2>>"$LOG_FILE" && onnx_ok=true || log_warn "onnxruntime install failed"
        fi
    fi

    if [[ "$onnx_ok" == true ]]; then
        local onnx_ver
        onnx_ver=$("$VENV_DIR/bin/python" -c "import onnxruntime; print(onnxruntime.__version__)" 2>/dev/null)
        log_ok "ONNX Runtime ${onnx_ver:-ok}"
    fi

    # ─── Install remaining backend dependencies ────────────────────────────
    log_info "Installing backend Python packages..."

    # Install in groups so partial failures are handled
    local pip_install="$VENV_DIR/bin/pip install"

    $pip_install "fastapi>=0.100.0" 2>>"$LOG_FILE" || log_warn "fastapi install failed"
    $pip_install "uvicorn[standard]>=0.20.0" 2>>"$LOG_FILE" || log_warn "uvicorn install failed"
    $pip_install "python-multipart>=0.0.5" 2>>"$LOG_FILE" || log_warn "python-multipart install failed"

    # opencv-python-headless preferred for server/headless environments
    if ! $pip_install "opencv-python-headless>=4.8.0" 2>>"$LOG_FILE"; then
        log_warn "opencv-python-headless failed, trying opencv-python..."
        $pip_install "opencv-python>=4.8.0" 2>>"$LOG_FILE" || log_warn "opencv-python install failed (non-fatal)"
    fi

    $pip_install "numpy>=1.24.0,<2.0.0" 2>>"$LOG_FILE" || log_warn "numpy install failed"
    $pip_install "Pillow>=10.0.0" 2>>"$LOG_FILE" || log_warn "Pillow install failed"
    $pip_install "piexif>=1.1.3" 2>>"$LOG_FILE" || log_warn "piexif install failed"
    $pip_install "pydantic>=2.0.0" 2>>"$LOG_FILE" || log_warn "pydantic install failed"

    # ─── Verify critical imports ───────────────────────────────────────────
    log_info "Verifying Python imports..."
    local failed_pkgs=()
    for pkg in onnxruntime cv2 numpy PIL fastapi uvicorn piexif pydantic; do
        if "$VENV_DIR/bin/python" -c "import $pkg" 2>/dev/null; then
            log_debug "  ✓ $pkg"
        else
            log_warn "  ✗ $pkg — import failed"
            failed_pkgs+=("$pkg")
        fi
    done

    if [[ ${#failed_pkgs[@]} -eq 0 ]]; then
        log_ok "All Python packages verified"
    else
        log_warn "Packages with issues: ${failed_pkgs[*]}"
        log_warn "Backend may not work fully until these are resolved."
        log_warn "Try: ${VENV_DIR}/bin/pip install ${failed_pkgs[*]}"
    fi

    return 0
}

# =============================================================================
# STEP 5: Frontend setup
# =============================================================================
step_frontend() {
    log_debug "Starting frontend setup..."

    if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
        log_error "No package.json at ${FRONTEND_DIR}"
        return 1
    fi

    # Check Node.js availability
    if ! cmd_exists node; then
        log_error "Node.js not found. Cannot set up frontend."
        return 1
    fi

    # Install npm dependencies
    if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
        log_info "node_modules exists — checking if up to date"
        # Simple check: compare package.json mtime vs node_modules mtime
        if [[ "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" ]] 2>/dev/null; then
            log_info "package.json newer than node_modules — reinstalling..."
            npm install --prefix "$FRONTEND_DIR" 2>>"$LOG_FILE" || {
                log_warn "npm install failed. Trying with --legacy-peer-deps..."
                npm install --prefix "$FRONTEND_DIR" --legacy-peer-deps 2>>"$LOG_FILE" || {
                    log_error "npm install failed after retry."
                    log_error "Check: node --version && npm --version"
                    return 1
                }
            }
        else
            log_ok "node_modules appears up to date"
        fi
    else
        log_info "Installing frontend dependencies..."
        npm install --prefix "$FRONTEND_DIR" 2>>"$LOG_FILE" || {
            log_warn "npm install failed. Trying with --legacy-peer-deps..."
            npm install --prefix "$FRONTEND_DIR" --legacy-peer-deps 2>>"$LOG_FILE" || {
                log_error "npm install failed."
                return 1
            }
        }
        log_ok "npm dependencies installed"
    fi

    # Build frontend for production
    log_info "Building frontend (Vite)..."
    npm run build --prefix "$FRONTEND_DIR" 2>>"$LOG_FILE" || {
        log_warn "Frontend build failed. Trying with --host flag..."
        # Some build failures are transient; try once more
        npm run build --prefix "$FRONTEND_DIR" 2>>"$LOG_FILE" || {
            log_warn "Build failed. Frontend can still run in dev mode."
            log_warn "Fix build errors then re-run: cd frontend && npm run build"
            return 1
        }
    }

    if [[ -d "$FRONTEND_DIR/dist" ]]; then
        log_ok "Frontend built: $(du -sh "$FRONTEND_DIR/dist" 2>/dev/null | cut -f1)"
    else
        log_warn "dist/ directory not found — build may have failed silently."
        return 1
    fi

    return 0
}

# =============================================================================
# STEP 6: Model file
# =============================================================================
step_model() {
    local target="$PROJECT_DIR/model.onnx"

    # If --model-path provided, copy from there
    if [[ -n "$CUSTOM_MODEL_PATH" ]]; then
        if [[ -f "$CUSTOM_MODEL_PATH" ]]; then
            log_info "Copying model from ${CUSTOM_MODEL_PATH}..."
            cp "$CUSTOM_MODEL_PATH" "$target" 2>/dev/null || {
                log_error "Failed to copy model from ${CUSTOM_MODEL_PATH}"
                return 1
            }
            log_ok "Model copied: $(du -h "$target" 2>/dev/null | cut -f1)"
            return 0
        else
            log_error "Specified model path not found: ${CUSTOM_MODEL_PATH}"
            return 1
        fi
    fi

    # Check if already present
    if [[ -f "$target" ]]; then
        log_ok "Model found: $(du -h "$target" 2>/dev/null | cut -f1)"
        return 0
    fi

    # Search common locations
    local search_paths=(
        "$PROJECT_DIR/model/best.onnx"
        "$PROJECT_DIR/runs/detect/runs/train/rescuevision_v13/weights/best.onnx"
        "$PROJECT_DIR/best.onnx"
    )

    for sp in "${search_paths[@]}"; do
        if [[ -f "$sp" ]]; then
            log_info "Found model at ${sp}, linking to ${target}..."
            ln -sf "$sp" "$target" 2>/dev/null || cp "$sp" "$target" 2>/dev/null
            if [[ -f "$target" ]]; then
                log_ok "Model linked: $(du -h "$target" 2>/dev/null | cut -f1)"
                return 0
            fi
        fi
    done

    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warn "  model.onnx not found!"
    log_warn ""
    log_warn "  The ONNX model file is needed for victim detection."
    log_warn "  Without it, the backend starts but inference is disabled."
    log_warn ""
    log_warn "  To fix this after setup:"
    log_warn "    cp /path/to/your/trained-model.onnx ${PROJECT_DIR}/model.onnx"
    log_warn "    sudo systemctl restart rescuevision-backend"
    log_warn ""
    log_warn "  Model search locations checked:"
    for sp in "${search_paths[@]}"; do
        log_warn "    - ${sp}"
    done
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    return 0  # Non-fatal
}

# =============================================================================
# STEP 7: Systemd backend service
# =============================================================================
step_backend_service() {
    local svc_file="/etc/systemd/system/rescuevision-backend.service"

    # Check if user exists
    if ! id "$PI_USER" &>/dev/null; then
        log_warn "User '${PI_USER}' does not exist. Using 'root' for service."
        local svc_user="root"
        local svc_group="root"
    else
        local svc_user="$PI_USER"
        local svc_group="$PI_USER"
    fi

    # Ensure venv and backend dir are accessible by the user
    if [[ "$svc_user" != "root" ]]; then
        chown -R "$svc_user":"$svc_group" "$VENV_DIR" 2>/dev/null || log_warn "Could not chown venv"
        chown -R "$svc_user":"$svc_group" "$BACKEND_DIR" 2>/dev/null || log_warn "Could not chown backend dir"
    fi

    log_info "Creating systemd service as user=${svc_user}..."

    cat > "$svc_file" << SERVICEEOF
[Unit]
Description=RescueVision Edge Backend (FastAPI + ONNX)
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${svc_user}
Group=${svc_group}
WorkingDirectory=${BACKEND_DIR}
Environment="PYTHONUNBUFFERED=1"
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload 2>/dev/null || true
    systemctl enable rescuevision-backend.service 2>/dev/null || {
        log_warn "Could not enable backend service (systemd may not be available)"
        return 0  # Non-fatal for containers
    }

    log_ok "Backend service created"
    return 0
}

# =============================================================================
# STEP 8: Nginx / frontend reverse proxy
# =============================================================================
step_nginx() {
    if [[ "$SKIP_NGINX" == true ]]; then
        log_info "Skipping Nginx setup (--skip-nginx)"
        return 0
    fi

    if ! cmd_exists nginx; then
        log_warn "Nginx not installed. Skipping web server setup."
        log_warn "Frontend: use 'cd frontend && npm run dev' in another terminal."
        return 0
    fi

    local frontend_dist="$FRONTEND_DIR/dist"
    if [[ ! -d "$frontend_dist" ]]; then
        log_warn "Frontend dist/ not found at ${frontend_dist}."
        log_warn "Nginx will be configured but serve nothing until you build the frontend."
        log_warn "Fix: cd frontend && npm run build"
    fi

    log_info "Configuring Nginx..."

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null

    cat > /etc/nginx/sites-available/rescuevision << NGINXEOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    client_max_body_size 100M;

    root ${frontend_dist};
    index index.html;

    # Proxy API requests to FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }

    location /detect {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /inject {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }

    location /export {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINXEOF

    # Enable site
    ln -sf /etc/nginx/sites-available/rescuevision /etc/nginx/sites-enabled/rescuevision

    # Test config
    if nginx -t 2>>"$LOG_FILE"; then
        log_ok "Nginx configuration valid"
        systemctl enable nginx 2>/dev/null || true
        systemctl restart nginx 2>/dev/null || log_warn "Nginx restart failed"
    else
        log_warn "Nginx configuration invalid — check /etc/nginx/sites-available/rescuevision"
        # Don't leave a broken symlink
        rm -f /etc/nginx/sites-enabled/rescuevision
        return 1
    fi

    return 0
}

# =============================================================================
# STEP 9: Firewall
# =============================================================================
step_firewall() {
    if ! cmd_exists ufw; then
        log_info "UFW not installed — skipping firewall (install: sudo apt-get install ufw)"
        return 0
    fi

    log_info "Configuring UFW..."
    ufw allow 80/tcp comment 'RescueVision Frontend' 2>>"$LOG_FILE" || true
    ufw allow 8000/tcp comment 'RescueVision API' 2>>"$LOG_FILE" || true

    if ! ufw status | grep -q "Status: active" 2>/dev/null; then
        ufw --force enable 2>>"$LOG_FILE" || log_warn "UFW enable failed (non-fatal)"
    fi

    log_ok "Firewall: ports 80, 8000 open"
    return 0
}

# =============================================================================
# Summary
# =============================================================================
show_summary() {
    local ip_addr
    ip_addr=$(hostname -I 2>/dev/null | awk '{print $1}')

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              RescueVision Edge — Setup Complete!            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ ${#FAILED_STEPS[@]} -gt 0 ]]; then
        echo -e "  ${RED}Steps with issues:${NC}"
        for s in "${FAILED_STEPS[@]}"; do
            echo -e "  ${RED}  ✗ ${s}${NC}"
        done
        echo ""
        echo -e "  ${YELLOW}Log file:${NC} ${LOG_FILE}"
        echo -e "  ${YELLOW}View errors:${NC} tail -50 ${LOG_FILE}"
        echo ""
    fi

    echo -e "  ${CYAN}Access URLs:${NC}"
    if [[ "$SKIP_NGINX" == false ]] && cmd_exists nginx; then
        echo -e "    Frontend (Nginx):  http://${ip_addr}/"
    fi
    echo -e "    Backend API:       http://${ip_addr}:8000"
    echo -e "    API Docs:          http://${ip_addr}:8000/docs"
    echo ""

    echo -e "  ${CYAN}Services:${NC}"
    if systemctl is-active --quiet rescuevision-backend.service 2>/dev/null; then
        echo -e "    ${GREEN}✓${NC} rescuevision-backend  (active)"
    else
        echo -e "    ${RED}✗${NC} rescuevision-backend  (inactive)"
    fi
    if systemctl is-active --quiet nginx 2>/dev/null; then
        echo -e "    ${GREEN}✓${NC} nginx                 (active)"
    else
        echo -e "    ${RED}✗${NC} nginx                 (inactive)"
    fi

    if [[ -f "$PROJECT_DIR/model.onnx" ]]; then
        echo -e "    ${GREEN}✓${NC} model.onnx            (present)"
    else
        echo -e "    ${RED}✗${NC} model.onnx            (missing)"
    fi
    echo ""

    echo -e "  ${YELLOW}Commands:${NC}"
    echo "    sudo systemctl start/stop/restart/status rescuevision-backend"
    echo "    sudo journalctl -u rescuevision-backend -f"
    echo "    source ${VENV_DIR}/bin/activate"
    echo ""

    if ! systemctl is-active --quiet rescuevision-backend.service 2>/dev/null; then
        echo -e "  ${YELLOW}Start backend:${NC}"
        echo "    sudo systemctl start rescuevision-backend"
        echo "    curl http://localhost:8000/health"
        echo ""
    fi

    if [[ ! -f "$PROJECT_DIR/model.onnx" ]]; then
        echo -e "  ${YELLOW}Model missing:${NC}"
        echo "    cp /path/to/your/model.onnx ${PROJECT_DIR}/model.onnx"
        echo "    sudo systemctl restart rescuevision-backend"
        echo ""
    fi
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    # Start fresh log
    : > "$LOG_FILE"

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        RescueVision Edge — Raspberry Pi Setup              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${GRAY}Log: ${LOG_FILE}${NC}"
    echo ""

    # ─── Run all steps (each is wrapped to catch failures) ────────────────
    run_step "Pre-flight checks"       step_preflight
    run_step "System packages"         step_system_packages
    run_step "Swap configuration"      step_swap
    run_step "Python environment"      step_python_env
    run_step "Frontend build"          step_frontend
    run_step "Model file"              step_model
    run_step "Backend service"         step_backend_service
    run_step "Nginx setup"             step_nginx
    run_step "Firewall"                step_firewall

    # ─── Start services ───────────────────────────────────────────────────
    echo ""
    echo -e "${CYAN}━━━ Starting services ━━━${NC}"
    systemctl daemon-reload 2>/dev/null || true
    systemctl start rescuevision-backend.service 2>/dev/null && log_ok "Backend started" || log_warn "Backend did not start (check: journalctl -u rescuevision-backend -n 20)"
    systemctl restart nginx 2>/dev/null && log_ok "Nginx restarted" || true

    # ─── Summary ──────────────────────────────────────────────────────────
    show_summary

    # ─── Final status ─────────────────────────────────────────────────────
    echo ""
    if [[ ${#FAILED_STEPS[@]} -eq 0 ]]; then
        echo -e "${GREEN}All steps completed successfully!${NC}"
    else
        echo -e "${YELLOW}${#FAILED_STEPS[@]} step(s) had issues (see above). Log: ${LOG_FILE}${NC}"
    fi

    local ip_addr
    ip_addr=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo -e "${GREEN}Open browser → http://${ip_addr}/${NC}"
    echo ""
}

main "$@"
