#!/bin/bash

# Surveillance AI Mobile App - Android Release Build Script
# This script builds a production-ready Android APK/AAB

set -e

echo "🚀 Starting Surveillance AI Android Release Build..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BUILD_TYPE="release"
OUTPUT_DIR="./android/app/build/outputs"
DATE=$(date +"%Y%m%d_%H%M%S")

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Android SDK is available
if ! command -v adb &> /dev/null; then
    print_error "Android SDK not found. Please install Android Studio and configure SDK."
    exit 1
fi

# Check if Java is available
if ! command -v java &> /dev/null; then
    print_error "Java not found. Please install Java 11 or higher."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "package.json not found. Please run this script from the project root."
    exit 1
fi

# Check if gradle.properties exists
if [ ! -f "android/gradle.properties" ]; then
    print_warning "android/gradle.properties not found. Using debug keystore."
    print_warning "For production builds, please create gradle.properties with release keystore details."
fi

print_success "Prerequisites check passed!"

# Clean previous builds
print_status "Cleaning previous builds..."
cd android
./gradlew clean
cd ..

# Install dependencies
print_status "Installing dependencies..."
npm ci

# Run tests
print_status "Running tests..."
npm test -- --watchAll=false --coverage=false

if [ $? -ne 0 ]; then
    print_error "Tests failed. Please fix issues before building release."
    exit 1
fi

print_success "All tests passed!"

# Build the release APK
print_status "Building release APK..."
cd android
./gradlew assembleRelease

if [ $? -ne 0 ]; then
    print_error "APK build failed!"
    exit 1
fi

print_success "APK build completed!"

# Build the release AAB (Android App Bundle)
print_status "Building release AAB..."
./gradlew bundleRelease

if [ $? -ne 0 ]; then
    print_error "AAB build failed!"
    exit 1
fi

print_success "AAB build completed!"

cd ..

# Copy outputs to release directory
print_status "Organizing release files..."
RELEASE_DIR="./releases/android/${DATE}"
mkdir -p "$RELEASE_DIR"

# Copy APK
if [ -f "${OUTPUT_DIR}/apk/release/app-release.apk" ]; then
    cp "${OUTPUT_DIR}/apk/release/app-release.apk" "${RELEASE_DIR}/surveillance-ai-${DATE}.apk"
    print_success "APK copied to ${RELEASE_DIR}/surveillance-ai-${DATE}.apk"
fi

# Copy AAB
if [ -f "${OUTPUT_DIR}/bundle/release/app-release.aab" ]; then
    cp "${OUTPUT_DIR}/bundle/release/app-release.aab" "${RELEASE_DIR}/surveillance-ai-${DATE}.aab"
    print_success "AAB copied to ${RELEASE_DIR}/surveillance-ai-${DATE}.aab"
fi

# Copy mapping files (if ProGuard is enabled)
if [ -f "${OUTPUT_DIR}/mapping/release/mapping.txt" ]; then
    cp "${OUTPUT_DIR}/mapping/release/mapping.txt" "${RELEASE_DIR}/mapping-${DATE}.txt"
    print_success "Mapping file copied to ${RELEASE_DIR}/mapping-${DATE}.txt"
fi

# Generate checksums
print_status "Generating checksums..."
cd "$RELEASE_DIR"
sha256sum *.apk *.aab > checksums.txt 2>/dev/null || true
cd - > /dev/null

# Display build information
print_success "🎉 Android release build completed successfully!"
echo ""
echo "📦 Build Information:"
echo "   Date: $DATE"
echo "   Type: $BUILD_TYPE"
echo "   Output Directory: $RELEASE_DIR"
echo ""
echo "📱 Generated Files:"
if [ -f "${RELEASE_DIR}/surveillance-ai-${DATE}.apk" ]; then
    APK_SIZE=$(du -h "${RELEASE_DIR}/surveillance-ai-${DATE}.apk" | cut -f1)
    echo "   📄 APK: surveillance-ai-${DATE}.apk (${APK_SIZE})"
fi
if [ -f "${RELEASE_DIR}/surveillance-ai-${DATE}.aab" ]; then
    AAB_SIZE=$(du -h "${RELEASE_DIR}/surveillance-ai-${DATE}.aab" | cut -f1)
    echo "   📦 AAB: surveillance-ai-${DATE}.aab (${AAB_SIZE})"
fi
echo ""
echo "🚀 Ready for deployment!"
echo "   - Upload AAB to Google Play Console"
echo "   - Test APK on various devices"
echo "   - Verify all features work correctly"
