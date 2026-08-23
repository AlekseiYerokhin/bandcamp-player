#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_DIR}/build"
APPDIR="${BUILD_DIR}/bandcamp-player.AppDir"
ARCH="${ARCH:-x86_64}"
APPIMAGE_NAME="Bandcamp-Player-${ARCH}.AppImage"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

cleanup() {
    log "Cleaning previous build..."
    rm -rf "${BUILD_DIR}"
    rm -rf "${PROJECT_DIR}/dist"
}

check_deps() {
    log "Checking build dependencies..."
    local missing=()

    command -v pyinstaller &>/dev/null || missing+=("pyinstaller")
    command -v wget &>/dev/null || command -v curl &>/dev/null || missing+=("wget or curl")

    if [ ${#missing[@]} -gt 0 ]; then
        err "Missing tools: ${missing[*]}\nInstall with: pip install pyinstaller"
    fi

    local vlc_found
    vlc_found="$(ldconfig -p | grep "libvlc.so" || true)"
    if [ -z "$vlc_found" ]; then
        err "libvlc not found. Install with:\n  Debian/Ubuntu: sudo apt install libvlc-dev vlc-plugin-base\n  Arch: sudo pacman -S vlc\n  Fedora: sudo dnf install vlc"
    fi

    log "All dependencies OK."
}

find_vlc_paths() {
    local ld_output
    ld_output="$(ldconfig -p)"
    
    VLC_LIB_DIR="$(echo "$ld_output" | grep 'libvlc.so.5' | head -1 | awk '{print $NF}' | xargs dirname)"
    VLC_CORE_LIB="$(echo "$ld_output" | grep 'libvlccore.so' | head -1 | awk '{print $NF}')"
    VLC_PLUGINS_DIR=""

    for candidate in \
        "${VLC_LIB_DIR}/vlc/plugins" \
        "/usr/lib/x86_64-linux-gnu/vlc/plugins" \
        "/usr/lib/vlc/plugins" \
        "/usr/lib64/vlc/plugins"; do
        if [ -d "$candidate" ]; then
            VLC_PLUGINS_DIR="$candidate"
            break
        fi
    done

    if [ -z "$VLC_LIB_DIR" ] || [ ! -d "$VLC_LIB_DIR" ]; then
        err "Cannot find libvlc.so.5"
    fi
    if [ -z "$VLC_PLUGINS_DIR" ]; then
        warn "Cannot find VLC plugins directory. Audio playback may not work."
    fi

    log "VLC lib dir:     ${VLC_LIB_DIR}"
    log "VLC core lib:    ${VLC_CORE_LIB}"
    log "VLC plugins dir: ${VLC_PLUGINS_DIR:-not found}"
}

run_pyinstaller() {
    log "Running PyInstaller..."
    cd "$PROJECT_DIR"
    pyinstaller bandcamp.spec --clean --noconfirm
    log "PyInstaller done."
}

build_appdir() {
    log "Building AppDir..."

    mkdir -p "${APPDIR}/usr/bin"
    mkdir -p "${APPDIR}/usr/lib"
    mkdir -p "${APPDIR}/usr/lib/vlc/plugins"
    mkdir -p "${APPDIR}/usr/share/applications"
    mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

    cp "${PROJECT_DIR}/dist/bandcamp-player" "${APPDIR}/usr/bin/bandcamp-player"
    chmod +x "${APPDIR}/usr/bin/bandcamp-player"

    find "${VLC_LIB_DIR}" -maxdepth 1 -name "libvlc.so*" -exec cp -L {} "${APPDIR}/usr/lib/" \;
    if [ -n "$VLC_CORE_LIB" ] && [ -f "$VLC_CORE_LIB" ]; then
        cp -L "$VLC_CORE_LIB" "${APPDIR}/usr/lib/"
    fi

    if [ -n "$VLC_PLUGINS_DIR" ] && [ -d "$VLC_PLUGINS_DIR" ]; then
        log "Copying VLC plugins (this may take a moment)..."
        cp -rL "${VLC_PLUGINS_DIR}/"* "${APPDIR}/usr/lib/vlc/plugins/" 2>/dev/null || true
    fi

    if [ -f "${PROJECT_DIR}/assets/icon32.png" ]; then
        cp "${PROJECT_DIR}/assets/icon32.png" "${APPDIR}/bandcamp-player.png"
    elif [ -f "${PROJECT_DIR}/assets/icon.png" ]; then
        cp "${PROJECT_DIR}/assets/icon.png" "${APPDIR}/bandcamp-player.png"
    fi

    if [ -f "${PROJECT_DIR}/assets/icon.png" ]; then
        cp "${PROJECT_DIR}/assets/icon.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/bandcamp-player.png"
    fi

    cp "${SCRIPT_DIR}/AppDir/bandcamp.desktop" "${APPDIR}/bandcamp-player.desktop"
    cp "${SCRIPT_DIR}/AppDir/bandcamp.desktop" "${APPDIR}/usr/share/applications/bandcamp-player.desktop"

    cp "${SCRIPT_DIR}/AppDir/AppRun" "${APPDIR}/AppRun"
    chmod +x "${APPDIR}/AppRun"

    if [ -f "${APPDIR}/bandcamp-player.png" ]; then
        ln -sf bandcamp-player.png "${APPDIR}/.DirIcon"
    fi

    log "AppDir built at: ${APPDIR}"
}

download_appimagetool() {
    local tool_path="${BUILD_DIR}/appimagetool"
    if [ -f "$tool_path" ]; then
        echo "$tool_path"
        return
    fi

    local url="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    log "Downloading appimagetool..." >&2

    if command -v wget &>/dev/null; then
        wget -q -O "$tool_path" "$url"
    else
        curl -sL -o "$tool_path" "$url"
    fi

    chmod +x "$tool_path"
    echo "$tool_path"
}

create_appimage() {
    log "Creating AppImage..."
    local appimagetool
    appimagetool="$(download_appimagetool)"

    cd "$BUILD_DIR"
    ARCH="${ARCH}" "$appimagetool" "${APPDIR}" "${APPIMAGE_NAME}"

    log "AppImage created: ${BUILD_DIR}/${APPIMAGE_NAME}"
    log "Size: $(du -sh "${BUILD_DIR}/${APPIMAGE_NAME}" | cut -f1)"
}

print_summary() {
    echo ""
    log "========================================="
    log "  Build complete!"
    log "  Output: ${BUILD_DIR}/${APPIMAGE_NAME}"
    log "========================================="
    echo ""
    log "To run:    ./${BUILD_DIR##${PROJECT_DIR}/}/${APPIMAGE_NAME}"
    log "To install: mv ${APPIMAGE_NAME} ~/Applications/"
    echo ""
}

main() {
    log "Building Bandcamp Player AppImage"
    log "Project dir: ${PROJECT_DIR}"
    log "Architecture: ${ARCH}"

    cleanup
    check_deps
    find_vlc_paths
    run_pyinstaller
    build_appdir
    create_appimage
    print_summary
}

main "$@"
