# 📱 Surveillance AI - Mobile App

> AI-Powered Surveillance System - React Native Mobile Application

[![React Native](https://img.shields.io/badge/React%20Native-0.73.2-blue.svg)](https://reactnative.dev/)
[![Platform](https://img.shields.io/badge/Platform-iOS%20%7C%20Android-lightgrey.svg)](https://reactnative.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/surveillance-ai/mobile-app)

## 🎯 Overview

The Surveillance AI mobile app provides comprehensive security monitoring capabilities directly from your smartphone. Built with React Native, it offers real-time camera feeds, AI-powered threat detection, instant alerts, and advanced security features across iOS and Android platforms.

## ✨ Key Features

### 🔒 **Advanced Security**
- **Biometric Authentication** - Face ID, Touch ID, Fingerprint
- **End-to-End Encryption** - Secure data transmission
- **Auto-Lock Protection** - Configurable timeout settings
- **Privacy Controls** - App switcher protection

### 📹 **Live Monitoring**
- **Real-Time Feeds** - HD video streaming from surveillance cameras
- **Multi-Camera View** - Monitor multiple cameras simultaneously
- **PTZ Controls** - Pan, tilt, zoom camera controls
- **Fullscreen Mode** - Immersive viewing experience

### 🚨 **Smart Alerts**
- **AI-Powered Detection** - Intelligent threat recognition
- **Push Notifications** - Instant security alerts
- **Priority Levels** - High, medium, low severity classification
- **Custom Filters** - Personalized alert preferences

### 📊 **Analytics Dashboard**
- **System Overview** - Real-time status monitoring
- **Security Metrics** - Comprehensive analytics
- **Event Timeline** - Chronological security events
- **Performance Insights** - System health monitoring

### 🌐 **Connectivity**
- **Real-Time Sync** - WebSocket-based live updates
- **Offline Mode** - Cached data access without internet
- **Background Sync** - Automatic data synchronization
- **Network Resilience** - Automatic reconnection handling

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **React Native CLI** or **Expo CLI**
- **Android Studio** (for Android development)
- **Xcode** (for iOS development - macOS only)

### Installation

```bash
# Clone the repository
git clone https://github.com/surveillance-ai/mobile-app.git
cd mobile-app

# Install dependencies
npm install

# iOS setup (macOS only)
cd ios && pod install && cd ..

# Android setup
# Ensure Android SDK and emulator are configured
```

### Development

```bash
# Start Metro bundler
npm start

# Run on Android
npm run android

# Run on iOS (macOS only)
npm run ios

# Run tests
npm test

# Run E2E tests
npm run test:e2e
```

## 🏗️ Architecture

### Technology Stack

- **Frontend**: React Native 0.73.2
- **State Management**: Redux Toolkit + Context API
- **Navigation**: React Navigation 6
- **Real-Time**: WebSocket integration
- **Authentication**: Biometric + Token-based
- **Storage**: AsyncStorage + Redux Persist
- **Testing**: Jest + Detox
- **CI/CD**: GitHub Actions

### Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Button.js       # Custom button component
│   ├── Card.js         # Card container component
│   ├── VideoPlayer.js  # Video streaming component
│   └── ...
├── screens/            # Screen components
│   ├── LoginScreen.js  # Authentication screen
│   ├── DashboardScreen.js # Main dashboard
│   ├── CamerasScreen.js   # Camera list view
│   ├── AlertsScreen.js    # Alerts management
│   └── ...
├── services/           # API and external services
│   ├── authService.js  # Authentication API
│   ├── cameraService.js # Camera management
│   ├── websocketService.js # Real-time communication
│   └── ...
├── store/              # Redux store configuration
│   ├── index.js        # Store setup
│   └── slices/         # Redux slices
├── contexts/           # React contexts
│   ├── AuthContext.js  # Authentication context
│   └── NetworkContext.js # Network monitoring
├── navigation/         # Navigation configuration
├── utils/             # Utility functions
├── constants/         # App constants
└── test/              # Test configuration
```

## 🔧 Configuration

### Environment Variables

Create environment files for different deployment stages:

```bash
# .env.development
API_BASE_URL=http://localhost:8001
WEBSOCKET_URL=ws://localhost:8002
ENV=development

# .env.production
API_BASE_URL=https://api.surveillance-ai.com
WEBSOCKET_URL=wss://ws.surveillance-ai.com
ENV=production
```

### Firebase Setup

1. Create Firebase project
2. Add Android/iOS apps to project
3. Download configuration files:
   - `google-services.json` → `android/app/`
   - `GoogleService-Info.plist` → `ios/SurveillanceApp/`
4. Configure push notifications

## 🧪 Testing

### Unit Testing

```bash
# Run all unit tests
npm run test:unit

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run integration tests
npm run test:integration
```

### E2E Testing

```bash
# Build Detox (first time setup)
npm run test:e2e:build

# Run E2E tests on Android
npm run test:e2e:android

# Run E2E tests on iOS
npm run test:e2e:ios

# Run production E2E tests
npm run test:e2e:production

# Run all tests (unit + E2E)
npm run test:all
```

### Configuration Testing

The app includes comprehensive configuration validation:

```bash
# Validate build configuration
node scripts/validate-build.js

# Test environment configuration
npm run test -- --testMatch='**/config/**/*.test.js'
```

### Test Coverage

Current test coverage targets:
- **Statements**: 70%+
- **Branches**: 70%+
- **Functions**: 70%+
- **Lines**: 70%+

Enhanced testing includes:
- ✅ **Unit Tests**: Components, services, utilities
- ✅ **Integration Tests**: Configuration, API integration
- ✅ **E2E Tests**: Complete user workflows
- ✅ **Configuration Validation**: Environment setup verification

## 📦 Build & Deployment

### Development Builds

```bash
# Android development
npm run android

# iOS development
npm run ios
```

### Production Builds

```bash
# Android release build
npm run release:android

# iOS release build
npm run release:ios

# Build both platforms
npm run release:all
```

### Store Deployment

1. **Android (Google Play)**
   ```bash
   # Generate release AAB
   npm run build:android:bundle
   
   # Upload to Google Play Console
   # Follow DEPLOYMENT_GUIDE.md
   ```

2. **iOS (App Store)**
   ```bash
   # Create archive
   npm run build:ios:archive
   
   # Upload to App Store Connect
   # Follow DEPLOYMENT_GUIDE.md
   ```

## 🔐 Security Features

### Authentication Methods
- **Email/Password** - Traditional login
- **Biometric** - Face ID, Touch ID, Fingerprint
- **Two-Factor** - SMS/Email verification (planned)

### Data Protection
- **Encryption at Rest** - Sensitive data encryption
- **Secure Communication** - HTTPS/WSS protocols
- **Certificate Pinning** - Enhanced connection security
- **Secure Storage** - Keychain/Keystore integration

### Privacy Controls
- **App Lock** - Automatic screen locking
- **Privacy Screen** - Background app protection
- **Data Minimization** - Only necessary data collection
- **User Consent** - Granular permission controls

## 📊 Performance

### Optimization Features
- **Memory Management** - Automatic cleanup and optimization
- **Image Caching** - Efficient image loading and caching
- **Background Tasks** - Smart background processing
- **Network Optimization** - Intelligent data fetching

### Monitoring
- **Crash Reporting** - Firebase Crashlytics integration
- **Performance Monitoring** - Real-time performance tracking
- **Analytics** - User behavior and app usage analytics
- **Memory Profiling** - Memory leak detection and optimization

## 🌐 Offline Support

### Cached Data
- Camera configurations
- Recent alerts
- User preferences
- Authentication tokens

### Sync Strategy
- **Automatic Sync** - When network is restored
- **Queue Management** - Failed requests queuing
- **Conflict Resolution** - Server-side conflict handling
- **Data Prioritization** - Critical data sync first

## 🚨 Push Notifications

### Notification Types
- **Security Alerts** - Immediate threat notifications
- **System Status** - Camera online/offline updates
- **Maintenance** - Scheduled maintenance alerts
- **Updates** - App and system updates

### Customization
- **Priority Levels** - Configure notification importance
- **Quiet Hours** - Scheduled notification silence
- **Alert Filters** - Choose which alerts to receive
- **Sound Settings** - Custom notification sounds

## 🤝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Install dependencies**: `npm install`
4. **Make changes and test**: `npm test`
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open Pull Request**

### Code Standards

- **ESLint** - JavaScript/TypeScript linting
- **Prettier** - Code formatting
- **Husky** - Git hooks for quality checks
- **Conventional Commits** - Standardized commit messages

### Testing Requirements

- Unit tests for new components
- E2E tests for new user flows
- Performance tests for critical paths
- Security tests for authentication flows

## 📝 Documentation

### Available Guides
- [**Deployment Guide**](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [**Assets Guide**](ASSETS_GUIDE.md) - App icons and screenshots
- [**API Documentation**](docs/API.md) - Backend API reference
- [**Architecture Guide**](docs/ARCHITECTURE.md) - Technical architecture details

### Development Resources
- [React Native Documentation](https://reactnative.dev/)
- [Firebase Documentation](https://firebase.google.com/docs)
- [Redux Toolkit Guide](https://redux-toolkit.js.org/)
- [React Navigation](https://reactnavigation.org/)

## 🐛 Troubleshooting

### Common Issues

#### Build Errors
```bash
# Clear Metro cache
npm run reset

# Clean builds
npm run clean

# Reinstall dependencies
rm -rf node_modules && npm install
```

#### iOS Specific
```bash
# Clean iOS build
cd ios && xcodebuild clean && cd ..

# Reinstall pods
cd ios && rm -rf Pods && pod install && cd ..
```

#### Android Specific
```bash
# Clean Android build
cd android && ./gradlew clean && cd ..

# Reset ADB
adb kill-server && adb start-server
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

### Getting Help
- **Documentation**: Check the guides in `/docs`
- **Issues**: Open a GitHub issue for bugs
- **Discussions**: Use GitHub Discussions for questions
- **Email**: support@surveillance-ai.com

### Enterprise Support
- **Priority Support** - 24/7 technical assistance
- **Custom Deployment** - Tailored deployment solutions
- **Training** - Team training and onboarding
- **SLA** - Service level agreements available

---

## 🎯 Roadmap

### Version 1.1.0 (Q2 2024)
- [ ] Multi-language support
- [ ] Enhanced video quality options
- [ ] Smart home integration
- [ ] Advanced analytics dashboard

### Version 1.2.0 (Q3 2024)
- [ ] Geofencing capabilities
- [ ] Voice commands
- [ ] AR overlays for camera feeds
- [ ] Machine learning insights

### Version 2.0.0 (Q4 2024)
- [ ] Complete UI redesign
- [ ] Edge AI processing
- [ ] Mesh network support
- [ ] Advanced automation rules

---

**Built with ❤️ by the Surveillance AI Team**

*Protecting what matters most through intelligent technology*
