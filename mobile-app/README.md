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
- **Alert Acknowledgment** - Two-way sync with offline support and optimistic updates

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
- **Offline Banner** - Visual indicator for offline status
- **Smart Caching** - Intelligent data caching strategies

### 📱 **Network & Offline Features**
- **Network Status Detection** - Real-time connectivity monitoring
- **Offline Queue** - Failed requests queued for retry
- **Cached Responses** - Smart caching with expiration
- **Offline Banner** - Persistent offline status indicator
- **Data Synchronization** - Automatic sync when connectivity restored

### 🔐 **Encrypted Offline Cache**
- **AES-256 Encryption** - Military-grade encryption for all offline data
- **Device-Unique Keys** - PBKDF2 key derivation from device identifiers
- **Secure Key Storage** - Biometric-protected key storage in Keychain/Keystore
- **Automatic Fallback** - Graceful handling of corrupted encrypted data
- **Zero-Knowledge** - No plaintext data stored on device
- **Migration Support** - Seamless upgrade from legacy storage

#### Security Implementation
- **Encryption**: AES-256-CBC with PBKDF2 key derivation (10,000 iterations)
- **Key Management**: Device-unique ID + secure random salt
- **Storage**: iOS Keychain / Android Keystore with biometric access control
- **Data Protection**: All user tokens, settings, and cache encrypted at rest

### 🔔 **Alert Acknowledgment System**

The mobile app provides comprehensive alert acknowledgment capabilities with full offline support and two-way synchronization.

#### **Core Features**
- **One-Tap Acknowledgment** - Acknowledge alerts directly from the alerts list
- **Optimistic Updates** - Instant UI feedback with local state updates
- **Offline Support** - Queue acknowledgments when offline using secure storage
- **Automatic Sync** - Auto-flush pending acknowledgments when connectivity restored
- **Visual Indicators** - Clear status display for acknowledged and pending sync states
- **Error Handling** - Graceful fallback to offline mode on API failures

#### **Implementation Details**

**API Integration**
```typescript
POST /api/v1/alerts/{alertId}/ack
Authorization: Bearer {token}
Content-Type: application/json

// Response: 200 OK with updated alert data
```

**Offline Persistence**
- Pending acknowledgments stored in `secureStorage` under key `pendingAcks`
- AES-256 encrypted storage with device-unique keys
- Automatic retry mechanism with exponential backoff
- Maximum retry attempts (3) with graceful failure handling

**Redux State Management**
```typescript
interface AlertsState {
  alerts: Alert[];
  pendingAcks: string[]; // Alert IDs pending sync
  syncStatus: 'idle' | 'syncing' | 'success' | 'error';
  loading: boolean;
  error: string | null;
}
```

**Network Integration**
- Automatic sync trigger on network reconnection
- Background sync prevention when app is not active
- Duplicate acknowledgment prevention
- Sync progress tracking with visual indicators

#### **User Experience**

**Visual States**
- **Normal Alert**: Standard alert card with "Acknowledge" button
- **Acknowledged Alert**: Reduced opacity (0.6) with visual confirmation
- **Pending Sync**: "⏳ Syncing..." indicator for offline acknowledgments
- **Sync Error**: Error state with retry option

**Offline Behavior**
1. User taps "Acknowledge" while offline
2. Alert immediately shows as acknowledged (optimistic update)
3. Acknowledgment queued in secure storage
4. "⏳ Syncing..." indicator appears
5. Auto-sync when network connection restored
6. Visual indicator removed on successful sync

#### **Error Scenarios**
- **API Timeout**: Automatic fallback to offline mode
- **Network Error**: Queue acknowledgment for later sync
- **Authentication Error**: Prompt user to re-login
- **Storage Error**: Fallback to in-memory queue with warning

### 📹 **Video Streaming**

The mobile app features advanced HLS (HTTP Live Streaming) adaptive bitrate support for optimal video streaming performance across different network conditions.

#### **Core Features**
- **Adaptive Bitrate Streaming** - Automatic quality adjustment based on network conditions
- **Manual Quality Selection** - User-controlled quality selection with 360p, 720p, 1080p, and 4K options
- **Auto Quality Toggle** - Smart switching between automatic and manual quality modes
- **Session Persistence** - User preferences saved and restored across app sessions
- **HLS Master Playlist Support** - Client-side parsing of m3u8 playlists for quality extraction
- **Optimized Buffering** - Custom buffer configuration for smooth playback

#### **Implementation Details**

**CameraView Component**
```typescript
import { CameraView } from '../components/CameraView';

// Basic usage with auto quality (default)
<CameraView hlsMasterPlaylistUrl="https://example.com/master.m3u8" />

// Advanced configuration
<CameraView
  hlsMasterPlaylistUrl="https://example.com/master.m3u8"
  isLive={true}
  autoPlay={true}
  controls={true}
  fullscreenEnabled={true}
  onFullscreenChange={(isFullscreen) => console.log('Fullscreen:', isFullscreen)}
  onError={(error) => console.error('Video error:', error)}
  onLoad={(data) => console.log('Video loaded:', data)}
/>
```

**HLS Configuration**
- **Skip Processing**: `skipProcessing: true` for direct HLS handling
- **Buffer Config**: Optimized buffering with 15s min buffer, 50s max buffer
- **Security**: Picture-in-picture and background play disabled for security
- **Headers**: Custom User-Agent for stream authentication

**Quality Management**
```typescript
// Quality levels extracted from HLS master playlist
interface QualityLevel {
  bandwidth: number;    // Stream bandwidth in bps
  resolution: string;   // Video resolution (e.g., "1920x1080")
  url: string;         // Direct stream URL
  label: string;       // Human-readable label (e.g., "1080p")
}

// Auto quality recommendations based on network type
- WiFi: Highest available quality
- 4G: High-medium quality
- 3G: Medium quality  
- 2G/Slow: Lowest quality
```

**User Preferences Persistence**
```typescript
// AsyncStorage keys for user preferences
const STORAGE_KEYS = {
  AUTO_QUALITY: 'camera_auto_quality_enabled',    // boolean
  SELECTED_QUALITY: 'camera_selected_quality',    // string (e.g., "720p")
};

// Settings persist across app sessions
// Auto Quality: ON by default for new users
// Manual Quality: Remembers last selected quality level
```

#### **HLS Parser Utility**

**Client-Side Playlist Parsing**
```typescript
import { HLSParser } from '../utils/hlsParser';

const parser = new HLSParser();
const qualities = await parser.parsePlaylist(masterPlaylistUrl);

// Extracted quality levels with meaningful labels
// Automatic bandwidth-based quality naming
// Resolution-based labels (360p, 720p, 1080p, 4K)
// Relative quality names (Low, Medium, High, Ultra High)
```

**Parser Features**
- **M3U8 Support**: Full parsing of HLS master playlists
- **URL Resolution**: Automatic relative-to-absolute URL conversion
- **Error Handling**: Graceful fallback to master playlist on parsing errors
- **Quality Labeling**: Intelligent quality naming based on resolution and bandwidth
- **Network Recommendations**: Quality suggestions based on connection type

#### **User Experience**

**Auto Quality Mode (Default)**
1. Video starts with automatic quality selection
2. Quality indicator shows "AUTO"
3. Player adapts quality based on network conditions
4. Smooth transitions without user intervention
5. Buffer health maintained during quality switches

**Manual Quality Selection**
1. Tap video to show controls
2. Tap quality/HD button to open quality modal
3. Toggle "Auto Quality" OFF to enable manual selection
4. Select desired quality level (360p, 720p, 1080p, etc.)
5. Quality switches within 5 seconds
6. Settings persist for future sessions

**Quality Modal Interface**
- **Auto Quality Toggle**: Enable/disable adaptive streaming
- **Quality Options**: List of available qualities with bandwidth info
- **Current Selection**: Highlighted current quality level
- **Bandwidth Display**: Shows kbps for each quality option
- **Close Button**: Apply selection and return to video

#### **Performance Optimizations**

**Buffer Configuration**
```typescript
bufferConfig: {
  minBufferMs: 15000,                    // 15s minimum buffer
  maxBufferMs: 50000,                    // 50s maximum buffer  
  bufferForPlaybackMs: 2500,             // 2.5s start playback
  bufferForPlaybackAfterRebufferMs: 5000 // 5s rebuffer threshold
}
```

**Network Adaptation**
- Real-time bandwidth monitoring
- Automatic quality switching based on buffer health
- Predictive quality selection for optimal viewing experience
- Graceful degradation during network congestion

**Memory Management**
- Efficient video player cleanup on component unmount
- Quality level caching for improved performance
- Minimal memory footprint during quality switches
- Background processing prevention for battery optimization

#### **Testing**

**Sample HLS URLs for Testing**
```typescript
// Apple's official test streams with multiple qualities
const TEST_STREAMS = {
  // Basic multi-bitrate stream (360p, 720p, 1080p)
  appleBasic: 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
  
  // Big Buck Bunny - Open source test content
  bigBuckBunny: 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
  
  // Sintel - High quality test stream
  sintel: 'https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8',
};

// Usage in CameraView
<CameraView hlsMasterPlaylistUrl={TEST_STREAMS.appleBasic} />
```

**Manual Test Cases**

*Test 1: Auto Quality Network Adaptation*
1. Load test stream with "Auto Quality" enabled (default)
2. Watch video for 30 seconds on stable WiFi
3. Switch to mobile data or simulate slow network
4. Verify quality automatically adapts without buffering
5. Check quality indicator shows "AUTO"
6. **Expected**: Smooth quality transitions based on network conditions

*Test 2: Manual Quality Selection (360p Verification)*
1. Tap video to show controls
2. Tap quality button (HD icon) to open modal
3. Turn OFF "Auto Quality" toggle
4. Select "360p" from available options
5. Verify video switches to 360p stream within 5 seconds
6. Check quality indicator shows "360P"
7. **Expected**: Video uses exactly 360p quality, no automatic switching

*Test 3: Settings Persistence*
1. Set manual quality to 720p and close app
2. Reopen app and navigate to video player
3. Verify 720p quality is still selected
4. Toggle Auto Quality ON and close app again
5. Reopen and verify Auto Quality is enabled
6. **Expected**: All user preferences persist across app sessions

*Test 4: Error Recovery*
1. Use invalid HLS URL: `https://invalid-url.com/playlist.m3u8`
2. Verify error message displays with retry button
3. Switch to valid URL and confirm recovery
4. Test network interruption during playback
5. **Expected**: Graceful error handling with recovery options

**Integration Tests**
```bash
# Run adaptive bitrate specific tests
npm test -- src/components/__tests__/CameraView.adaptive.test.tsx

# Run all video player tests
npm test -- --testMatch='**/*CameraView*.test.tsx'

# Manual testing component (for development)
# Import ManualAdaptiveBitrateTest in your app for interactive testing
```

**Manual Testing Component**
```typescript
import ManualAdaptiveBitrateTest from './src/components/__tests__/ManualAdaptiveBitrateTest';

// Add to your development/debug screens
<ManualAdaptiveBitrateTest />
```

**Network Simulation Testing**
```bash
# iOS Simulator - Network Link Conditioner
# Enable in: Settings > Developer > Network Link Conditioner
# Profiles: WiFi, 4G, 3G, Edge, Very Bad Network

# Android Emulator - Network Speed Simulation
# In Extended Controls > Cellular > Network Speed
# Options: Full, LTE, 3G, HSPDA, EDGE, GPRS
```

**Quality Verification Tools**
```bash
# Monitor network requests in browser developer tools
# Look for different .m3u8 segment requests
# Verify bandwidth usage matches selected quality

# Video analysis tools
ffprobe <stream_url>  # Check stream properties
curl -I <stream_url>  # Verify stream accessibility
```

**Test Coverage**
- Component integration with react-native-video HLS support
- HLS parser functionality with hls-parser library
- AsyncStorage persistence for quality preferences  
- Automatic and manual quality switching scenarios
- Error recovery and network resilience
- Buffer configuration optimization for smooth playback

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

### Network & Offline Testing

Comprehensive testing for network status detection and offline functionality:

#### **Automated Tests**

```bash
# Run all network tests
npm test -- --testNamePattern="Network"

# Run specific offline tests
npm test -- --testPathPattern="network.test.tsx"

# Run with coverage for network features
npm test -- --coverage --testPathPattern="network"
```

#### **Manual Offline Testing**

**1. Network Status Detection**
```bash
# Start development server
npm start

# Run on device/emulator
npm run android  # or npm run ios

# Test connectivity changes:
# - Enable/disable Wi-Fi
# - Enable/disable mobile data
# - Switch to airplane mode
# - Move between different network environments
```

**2. Offline Banner Testing**
- Verify offline banner appears when disconnected
- Check banner disappears when reconnected
- Test banner animation (smooth slide in/out)
- Verify banner doesn't interfere with app navigation

**3. Offline Data Caching**
```javascript
// Test cached data access
// 1. Load data while online
// 2. Go offline
// 3. Verify cached data is still accessible
// 4. Check cache expiration (default: 5 minutes)
```

**4. Offline Request Queue**
```javascript
// Test request queuing
// 1. Go offline
// 2. Trigger API calls (camera actions, alerts)
// 3. Verify requests are queued
// 4. Go online
// 5. Verify queued requests are processed
```

**5. Data Synchronization**
```javascript
// Test sync behavior
// 1. Make changes while offline
// 2. Go online
// 3. Verify data syncs automatically
// 4. Check conflict resolution
```

#### **Testing Environments**

**Android Emulator:**
```bash
# Simulate network conditions
# 1. Open emulator
# 2. Settings > Network & Internet
# 3. Toggle Wi-Fi/Mobile data
# Or use Android Studio network condition simulation
```

**iOS Simulator:**
```bash
# Simulate network conditions
# 1. Open simulator
# 2. Device > Network Link Conditioner
# 3. Choose different network profiles
# Or use Hardware > Device > Network Conditions
```

**Physical Device:**
```bash
# Real-world testing
# 1. Install development build
# 2. Test in areas with poor connectivity
# 3. Test network switching (Wi-Fi to cellular)
# 4. Test in subway/elevator (no signal)
```

#### **Network Condition Simulation**

**Using Metro/React Native:**
```bash
# Slow 3G simulation
npm start -- --reset-cache

# Use Chrome DevTools Network tab for additional testing
```

**Using Third-Party Tools:**
```bash
# Network Link Conditioner (iOS)
# Charles Proxy for request inspection
# Flipper for network debugging
```

#### **Test Scenarios to Validate**

**✅ Network Detection**
- [ ] App detects initial network status
- [ ] Network changes are detected immediately
- [ ] Redux state updates correctly
- [ ] AsyncStorage persistence works

**✅ Offline UI**
- [ ] Offline banner appears/disappears correctly
- [ ] Banner animation is smooth
- [ ] Banner height animation works
- [ ] App remains functional with banner

**✅ Data Caching**
- [ ] API responses are cached
- [ ] Cache expiration works (5min default)
- [ ] Cached data serves when offline
- [ ] Cache clears on user logout

**✅ Request Queue**
- [ ] Failed requests are queued
- [ ] Queue persists across app restarts
- [ ] Queued requests execute when online
- [ ] Queue handles request failures

**✅ Data Sync**
- [ ] Background sync when network restored
- [ ] Sync indicator shows during sync
- [ ] Conflict resolution works
- [ ] User feedback for sync status

**✅ Performance**
- [ ] No memory leaks in network listener
- [ ] Efficient cache management
- [ ] Queue doesn't grow indefinitely
- [ ] Smooth animations during state changes

#### **Debugging Network Issues**

**Logging & Monitoring:**
```bash
# Enable network debugging
# Set up Flipper network inspector
# Use React Native Debugger
# Monitor Redux DevTools for network state
```

**Common Issues & Solutions:**
```bash
# Network listener not working
# - Check NetInfo permissions
# - Verify subscription cleanup

# Cache not working
# - Check AsyncStorage permissions
# - Verify cache key generation

# Queue not processing
# - Check network state updates
# - Verify queue persistence
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
- ✅ **Network Tests**: Offline functionality, caching, sync
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

## 🎯 Project Status

### ✅ **Completed Features**
- **Network Detection** - Real-time connectivity monitoring with @react-native-community/netinfo
- **Redux Integration** - NetworkSlice with isConnected and lastChecked state management  
- **Offline Banner** - Persistent visual indicator with smooth animations
- **Smart Caching** - 5-minute default cache with AsyncStorage persistence
- **Offline Queue** - Failed request queuing with automatic retry on reconnection
- **TypeScript Support** - Enhanced type safety and developer experience

### 🚧 **Current Status**
- Core network functionality implemented and tested
- Main App entry point updated to use new TypeScript App.tsx
- Comprehensive test suite created (some tests need Jest configuration fixes)
- Documentation and offline testing guide complete

### 🔧 **Quick Testing**
To test the offline functionality in development:

```bash
# Start the development server
npm start

# Run on device/emulator
npm run android  # or npm run ios

# Test offline mode by:
# 1. Toggling airplane mode
# 2. Disabling Wi-Fi/cellular data
# 3. Observing the offline banner appear/disappear
```

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
