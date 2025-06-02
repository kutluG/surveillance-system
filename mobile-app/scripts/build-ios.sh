#!/bin/bash

# Surveillance AI Mobile App - iOS Release Build Script
# This script builds a production-ready iOS IPA

set -e

echo "🍎 Starting Surveillance AI iOS Release Build..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCHEME="SurveillanceApp"
CONFIGURATION="Release"
WORKSPACE="ios/SurveillanceApp.xcworkspace"
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

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "iOS builds can only be created on macOS"
    exit 1
fi

# Check if Xcode is available
if ! command -v xcodebuild &> /dev/null; then
    print_error "Xcode not found. Please install Xcode from the App Store."
    exit 1
fi

# Check if CocoaPods is available
if ! command -v pod &> /dev/null; then
    print_error "CocoaPods not found. Please install CocoaPods: sudo gem install cocoapods"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "package.json not found. Please run this script from the project root."
    exit 1
fi

print_success "Prerequisites check passed!"

# Install dependencies
print_status "Installing dependencies..."
npm ci

# Install iOS dependencies
print_status "Installing iOS dependencies..."
cd ios
pod install --repo-update
cd ..

# Run tests
print_status "Running tests..."
npm test -- --watchAll=false --coverage=false

if [ $? -ne 0 ]; then
    print_error "Tests failed. Please fix issues before building release."
    exit 1
fi

print_success "All tests passed!"

# Clean previous builds
print_status "Cleaning previous builds..."
xcodebuild clean -workspace "$WORKSPACE" -scheme "$SCHEME" -configuration "$CONFIGURATION"

# Build the app for generic iOS device
print_status "Building iOS app for generic device..."
xcodebuild build -workspace "$WORKSPACE" \
    -scheme "$SCHEME" \
    -configuration "$CONFIGURATION" \
    -destination generic/platform=iOS \
    -allowProvisioningUpdates

if [ $? -ne 0 ]; then
    print_error "iOS build failed!"
    exit 1
fi

print_success "iOS build completed!"

# Archive the app
print_status "Creating iOS archive..."
ARCHIVE_PATH="./releases/ios/${DATE}/${SCHEME}.xcarchive"
mkdir -p "./releases/ios/${DATE}"

xcodebuild archive -workspace "$WORKSPACE" \
    -scheme "$SCHEME" \
    -configuration "$CONFIGURATION" \
    -archivePath "$ARCHIVE_PATH" \
    -allowProvisioningUpdates

if [ $? -ne 0 ]; then
    print_error "iOS archive failed!"
    exit 1
fi

print_success "iOS archive created!"

# Export options (for different distribution methods)
print_status "Creating export options..."

# App Store export options
cat > "./releases/ios/${DATE}/ExportOptions-AppStore.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store</string>
    <key>uploadBitcode</key>
    <false/>
    <key>uploadSymbols</key>
    <true/>
    <key>compileBitcode</key>
    <false/>
</dict>
</plist>
EOF

# Ad Hoc export options
cat > "./releases/ios/${DATE}/ExportOptions-AdHoc.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>ad-hoc</string>
    <key>uploadBitcode</key>
    <false/>
    <key>uploadSymbols</key>
    <true/>
    <key>compileBitcode</key>
    <false/>
</dict>
</plist>
EOF

# Export IPA for App Store
print_status "Exporting IPA for App Store..."
xcodebuild -exportArchive \
    -archivePath "$ARCHIVE_PATH" \
    -exportPath "./releases/ios/${DATE}/AppStore" \
    -exportOptionsPlist "./releases/ios/${DATE}/ExportOptions-AppStore.plist"

if [ $? -eq 0 ]; then
    print_success "App Store IPA exported successfully!"
else
    print_warning "App Store IPA export failed (may require valid provisioning profiles)"
fi

# Export IPA for Ad Hoc distribution
print_status "Exporting IPA for Ad Hoc distribution..."
xcodebuild -exportArchive \
    -archivePath "$ARCHIVE_PATH" \
    -exportPath "./releases/ios/${DATE}/AdHoc" \
    -exportOptionsPlist "./releases/ios/${DATE}/ExportOptions-AdHoc.plist"

if [ $? -eq 0 ]; then
    print_success "Ad Hoc IPA exported successfully!"
else
    print_warning "Ad Hoc IPA export failed (may require valid provisioning profiles)"
fi

# Generate checksums
print_status "Generating checksums..."
cd "./releases/ios/${DATE}"
find . -name "*.ipa" -exec sha256sum {} \; > checksums.txt 2>/dev/null || true
cd - > /dev/null

# Display build information
print_success "🎉 iOS release build completed successfully!"
echo ""
echo "📦 Build Information:"
echo "   Date: $DATE"
echo "   Configuration: $CONFIGURATION"
echo "   Scheme: $SCHEME"
echo "   Output Directory: ./releases/ios/${DATE}"
echo ""
echo "📱 Generated Files:"
if [ -d "./releases/ios/${DATE}/AppStore" ]; then
    echo "   🏪 App Store IPA: ./releases/ios/${DATE}/AppStore/"
fi
if [ -d "./releases/ios/${DATE}/AdHoc" ]; then
    echo "   📦 Ad Hoc IPA: ./releases/ios/${DATE}/AdHoc/"
fi
echo "   📄 Archive: $ARCHIVE_PATH"
echo ""
echo "🚀 Next Steps:"
echo "   - Test IPA on various iOS devices"
echo "   - Upload to App Store Connect using Xcode or Application Loader"
echo "   - Submit for App Store review"
echo "   - Distribute Ad Hoc build for internal testing"
