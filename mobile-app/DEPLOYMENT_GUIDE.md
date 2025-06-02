# Surveillance AI Mobile App - Deployment Guide

## Overview
This guide covers the complete deployment process for the Surveillance AI mobile application on both Android and iOS platforms.

## Prerequisites

### General Requirements
- Node.js 18+ and npm
- Git for version control
- Valid developer accounts (Google Play, Apple Developer)

### Android Requirements
- Android Studio with SDK
- Java 11 or higher
- Android SDK Build Tools 34.0.0+
- Release keystore for signing

### iOS Requirements (macOS only)
- Xcode 14+ 
- CocoaPods
- Valid iOS Distribution Certificate
- App Store provisioning profiles

## Build Configuration

### Environment Setup

1. **Clone and Install Dependencies**
   ```bash
   git clone <repository-url>
   cd mobile-app
   npm install
   ```

2. **Configure Environment Variables**
   Create `.env` files for different environments:
   ```bash
   # .env.development
   API_BASE_URL=http://localhost:8001
   WEBSOCKET_URL=ws://localhost:8002
   
   # .env.production
   API_BASE_URL=https://api.surveillance-ai.com
   WEBSOCKET_URL=wss://ws.surveillance-ai.com
   ```

## Android Deployment

### 1. Keystore Setup
```bash
# Generate release keystore
keytool -genkey -v -keystore surveillance-release-key.keystore \
  -alias surveillance-key-alias -keyalg RSA -keysize 2048 -validity 10000

# Move keystore to android/app/
mv surveillance-release-key.keystore android/app/
```

### 2. Configure Release Signing
Create `android/gradle.properties`:
```properties
SURVEILLANCE_UPLOAD_STORE_FILE=surveillance-release-key.keystore
SURVEILLANCE_UPLOAD_STORE_PASSWORD=your_keystore_password
SURVEILLANCE_UPLOAD_KEY_ALIAS=surveillance-key-alias
SURVEILLANCE_UPLOAD_KEY_PASSWORD=your_key_password
```

### 3. Build Release
```bash
# Make build script executable
chmod +x scripts/build-android.sh

# Run build script
./scripts/build-android.sh
```

### 4. Google Play Console Upload
1. Login to [Google Play Console](https://play.google.com/console)
2. Create new application
3. Upload the generated AAB file
4. Complete store listing information
5. Submit for review

## iOS Deployment

### 1. Provisioning Setup
1. Create App ID in Apple Developer Portal
2. Generate Distribution Certificate
3. Create App Store provisioning profile
4. Download and install certificates

### 2. Build Release
```bash
# Make build script executable
chmod +x scripts/build-ios.sh

# Run build script (macOS only)
./scripts/build-ios.sh
```

### 3. App Store Connect Upload
1. Login to [App Store Connect](https://appstoreconnect.apple.com)
2. Create new app
3. Upload IPA using Xcode or Application Loader
4. Complete app information
5. Submit for review

## Store Listing Optimization

### App Store Assets Required

#### Android (Google Play)
- **App Icon**: 512x512px PNG
- **Feature Graphic**: 1024x500px JPG/PNG
- **Screenshots**: 
  - Phone: 16:9 or 9:16 ratio
  - Tablet: 16:10 or 10:16 ratio
- **Short Description**: 80 characters max
- **Full Description**: 4000 characters max

#### iOS (App Store)
- **App Icon**: 1024x1024px PNG
- **Screenshots**:
  - iPhone: 1284x2778px, 1170x2532px
  - iPad: 2048x2732px
- **App Preview**: 15-30 second videos (optional)
- **Description**: No character limit

### Key Listing Elements

#### Title & Subtitle
- **Android**: "Surveillance AI - Security Monitor"
- **iOS**: "Surveillance AI" (subtitle: "AI-Powered Security")

#### Description Template
```
Transform your security monitoring with Surveillance AI - the most advanced mobile surveillance system powered by artificial intelligence.

🎯 REAL-TIME MONITORING
• Live HD camera feeds
• AI-powered threat detection
• Instant security alerts

🔒 ADVANCED SECURITY
• Biometric authentication
• End-to-end encryption
• Secure cloud storage

📱 MOBILE OPTIMIZED
• Intuitive smartphone interface
• Offline mode support
• Cross-device synchronization

Perfect for homes, businesses, and security professionals.
```

#### Keywords
```
surveillance, security, camera, monitoring, AI, alerts, biometric, 
real-time, video, protection, home security, business surveillance
```

## Testing Strategy

### Pre-Release Testing

1. **Unit Testing**
   ```bash
   npm test
   ```

2. **E2E Testing**
   ```bash
   npm run test:e2e
   ```

3. **Device Testing**
   - Test on various Android devices (different versions/manufacturers)
   - Test on various iOS devices (iPhone/iPad, different iOS versions)
   - Test different screen sizes and orientations

4. **Feature Testing**
   - Biometric authentication
   - Push notifications
   - Camera streaming
   - Offline functionality
   - Background sync

### Beta Testing

#### Android Beta (Google Play Console)
1. Create internal testing track
2. Upload AAB to internal track
3. Add internal testers
4. Distribute for feedback

#### iOS Beta (TestFlight)
1. Upload build to App Store Connect
2. Configure TestFlight
3. Add external testers
4. Distribute for feedback

## Release Process

### Version Management
```json
{
  "version": "1.0.0",
  "android": {
    "versionCode": 1
  },
  "ios": {
    "buildNumber": "1"
  }
}
```

### Release Checklist

#### Pre-Release
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Release notes prepared
- [ ] Store assets created
- [ ] Certificates/profiles valid

#### Android Release
- [ ] AAB built and signed
- [ ] Upload to Google Play Console
- [ ] Store listing completed
- [ ] Content rating assigned
- [ ] Submit for review

#### iOS Release
- [ ] IPA built and signed
- [ ] Upload to App Store Connect
- [ ] App information completed
- [ ] Privacy information provided
- [ ] Submit for review

#### Post-Release
- [ ] Monitor crash reports
- [ ] Check user reviews
- [ ] Monitor app performance
- [ ] Plan next version

## Continuous Deployment

### GitHub Actions (Optional)
Create `.github/workflows/deploy.yml` for automated builds:

```yaml
name: Deploy Mobile App

on:
  push:
    tags:
      - 'v*'

jobs:
  android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Build Android
        run: ./scripts/build-android.sh

  ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Build iOS
        run: ./scripts/build-ios.sh
```

## Monitoring & Analytics

### Crash Reporting
- **Android**: Firebase Crashlytics
- **iOS**: Firebase Crashlytics + Xcode Organizer

### Performance Monitoring
- Firebase Performance Monitoring
- React Native Performance Monitor

### User Analytics
- Firebase Analytics
- Custom event tracking for security features

## Support & Maintenance

### Post-Launch Support
1. Monitor app store reviews
2. Address critical bugs immediately
3. Regular security updates
4. Feature updates based on user feedback

### Update Strategy
- **Patch Updates** (1.0.x): Bug fixes, security updates
- **Minor Updates** (1.x.0): New features, improvements
- **Major Updates** (x.0.0): Major overhauls, breaking changes

## Security Considerations

### Data Protection
- Encrypt sensitive data at rest
- Use HTTPS/WSS for all communications
- Implement certificate pinning
- Regular security audits

### App Security
- Code obfuscation for release builds
- Anti-tampering measures
- Secure storage for credentials
- Biometric authentication

## Compliance

### Privacy Compliance
- GDPR compliance for EU users
- CCPA compliance for California users
- Clear privacy policy
- User consent management

### Security Standards
- SOC 2 Type II compliance
- ISO 27001 alignment
- Regular penetration testing
- Vulnerability assessments

---

For technical support or deployment issues, contact: support@surveillance-ai.com
