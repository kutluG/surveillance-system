# App Icon & Splash Screen Guide

## App Icon Requirements

### Android Icons (res/mipmap-*)
Required sizes for Android:
- `mdpi`: 48x48px
- `hdpi`: 72x72px  
- `xhdpi`: 96x96px
- `xxhdpi`: 144x144px
- `xxxhdpi`: 192x192px

Round icon versions:
- Same sizes with `_round` suffix
- Circular design optimized

### iOS Icons (Assets.xcassets/AppIcon.appiconset)
Required sizes for iOS:
- `20pt`: 20x20px, 40x40px, 60x60px
- `29pt`: 29x29px, 58x58px, 87x87px
- `40pt`: 40x40px, 80x80px, 120x120px
- `60pt`: 120x120px, 180x180px
- `1024pt`: 1024x1024px (App Store)

## Design Guidelines

### Visual Identity
- **Primary Color**: #007AFF (iOS Blue)
- **Secondary Color**: #5856D6 (Purple)
- **Background**: Dark theme optimized
- **Icon Style**: Modern, minimal, tech-focused

### Icon Concept
```
🎯 Central surveillance camera lens
🛡️ Security shield overlay
📱 Mobile device frame
🤖 AI circuit pattern background
```

### Design Elements
1. **Camera Lens**: Central focal point
2. **Shield Shape**: Security emphasis  
3. **Circuit Pattern**: AI technology
4. **Gradient**: Modern depth effect

## Icon Generation Script

Create icons from master file:

```bash
#!/bin/bash
# Generate app icons from master 1024x1024 file

MASTER_ICON="master-icon.png"
ANDROID_DIR="android/app/src/main/res"
IOS_DIR="ios/SurveillanceApp/Images.xcassets/AppIcon.appiconset"

# Android icons
sips -Z 48 "$MASTER_ICON" --out "$ANDROID_DIR/mipmap-mdpi/ic_launcher.png"
sips -Z 72 "$MASTER_ICON" --out "$ANDROID_DIR/mipmap-hdpi/ic_launcher.png"
sips -Z 96 "$MASTER_ICON" --out "$ANDROID_DIR/mipmap-xhdpi/ic_launcher.png"
sips -Z 144 "$MASTER_ICON" --out "$ANDROID_DIR/mipmap-xxhdpi/ic_launcher.png"
sips -Z 192 "$MASTER_ICON" --out "$ANDROID_DIR/mipmap-xxxhdpi/ic_launcher.png"

# iOS icons
sips -Z 40 "$MASTER_ICON" --out "$IOS_DIR/Icon-40.png"
sips -Z 58 "$MASTER_ICON" --out "$IOS_DIR/Icon-58.png"
sips -Z 60 "$MASTER_ICON" --out "$IOS_DIR/Icon-60.png"
sips -Z 80 "$MASTER_ICON" --out "$IOS_DIR/Icon-80.png"
sips -Z 87 "$MASTER_ICON" --out "$IOS_DIR/Icon-87.png"
sips -Z 120 "$MASTER_ICON" --out "$IOS_DIR/Icon-120.png"
sips -Z 180 "$MASTER_ICON" --out "$IOS_DIR/Icon-180.png"
sips -Z 1024 "$MASTER_ICON" --out "$IOS_DIR/Icon-1024.png"
```

## Splash Screen Configuration

### Android Splash Screen
File: `android/app/src/main/res/drawable/launch_screen.xml`

### iOS Launch Screen
File: `ios/SurveillanceApp/LaunchScreen.storyboard`

### React Native Splash Screen
Using `react-native-splash-screen` package:

```javascript
// App.js
import SplashScreen from 'react-native-splash-screen';

export default class App extends Component {
  componentDidMount() {
    SplashScreen.hide();
  }
}
```

## Store Screenshots

### Android Screenshots
Required sizes:
- Phone: 320px - 3840px (16:9 ratio)
- Tablet: 1200px - 3840px (16:10 ratio)
- Android TV: 1280x720px

### iOS Screenshots
Required sizes:
- iPhone 6.7": 1284x2778px
- iPhone 6.5": 1242x2688px  
- iPhone 5.5": 1242x2208px
- iPad Pro 12.9": 2048x2732px
- iPad Pro 11": 1668x2388px

### Screenshot Content
1. **Dashboard View**: Main monitoring interface
2. **Camera Feed**: Live video streaming
3. **Alerts Panel**: Security notifications
4. **Settings Screen**: Configuration options
5. **Login Screen**: Biometric authentication

## Asset Creation Tools

### Recommended Tools
- **Design**: Figma, Sketch, Adobe Illustrator
- **Icon Generation**: App Icon Generator websites
- **Screenshot Creation**: Xcode Simulator, Android Emulator
- **Image Optimization**: ImageOptim, TinyPNG

### Online Generators
- AppIcon.co - Generate all icon sizes
- LaunchScreen.storyboard - iOS splash screens
- Android Asset Studio - Android icons and assets

## Implementation Steps

1. **Create Master Assets**
   - Design 1024x1024 app icon
   - Create splash screen design
   - Plan screenshot composition

2. **Generate Platform Assets**
   - Run icon generation script
   - Configure splash screens
   - Create all required sizes

3. **Implement in App**
   - Update Android manifest
   - Configure iOS asset catalog
   - Test on all target devices

4. **Store Preparation**
   - Capture screenshots on target devices
   - Optimize for store display
   - Create feature graphics/videos

## Quality Checklist

### Icon Requirements
- [ ] High contrast and visibility
- [ ] Readable at small sizes
- [ ] Consistent with brand identity
- [ ] Optimized file sizes
- [ ] All required sizes generated

### Splash Screen
- [ ] Fast loading display
- [ ] Consistent with app theme
- [ ] Proper aspect ratio handling
- [ ] Smooth transition to app

### Screenshots
- [ ] Representative of key features
- [ ] High quality and clear
- [ ] Proper device framing
- [ ] Optimized for store display
- [ ] Localized if necessary

---

**Note**: Always test icons and splash screens on actual devices to ensure proper display across different screen densities and sizes.
