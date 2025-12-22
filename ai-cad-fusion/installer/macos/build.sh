#!/bin/bash
# Build script for FusionMCPBridge macOS PKG installer
# Requires: Xcode Command Line Tools (pkgbuild, productbuild)

set -e

VERSION="${1:-0.1.0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
OUTPUT_DIR="${SCRIPT_DIR}/output"
BUNDLE_NAME="FusionMCPBridge.bundle"

echo "Building FusionMCPBridge PKG installer v${VERSION}"
echo "Source: ${PLUGIN_ROOT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Create staging directory with correct structure
STAGING_DIR="${OUTPUT_DIR}/staging"
rm -rf "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}/Library/Application Support/Autodesk/ApplicationPlugins"

# Copy bundle to staging
cp -R "${PLUGIN_ROOT}/${BUNDLE_NAME}" \
    "${STAGING_DIR}/Library/Application Support/Autodesk/ApplicationPlugins/"

# Build the component package
echo "Creating component package..."
pkgbuild \
    --root "${STAGING_DIR}" \
    --identifier "com.cabinlab.fusionmcpbridge" \
    --version "${VERSION}" \
    --install-location "/" \
    "${OUTPUT_DIR}/FusionMCPBridge-component.pkg"

# Build the product package with distribution
echo "Creating distribution package..."
productbuild \
    --distribution "${SCRIPT_DIR}/distribution.xml" \
    --package-path "${OUTPUT_DIR}" \
    --version "${VERSION}" \
    "${OUTPUT_DIR}/FusionMCPBridge-${VERSION}-macos.pkg"

# Cleanup
rm -rf "${STAGING_DIR}"
rm -f "${OUTPUT_DIR}/FusionMCPBridge-component.pkg"

# Report success
PKG_PATH="${OUTPUT_DIR}/FusionMCPBridge-${VERSION}-macos.pkg"
if [ -f "${PKG_PATH}" ]; then
    SIZE=$(du -h "${PKG_PATH}" | cut -f1)
    echo ""
    echo "SUCCESS: Built ${PKG_PATH} (${SIZE})"
else
    echo "ERROR: PKG file was not created"
    exit 1
fi
