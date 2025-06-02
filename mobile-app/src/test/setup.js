import 'react-native-gesture-handler/jestSetup';
import mockAsyncStorage from '@react-native-async-storage/async-storage/jest/async-storage-mock';
import { jest } from '@jest/globals';

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => mockAsyncStorage);

// Mock React Native modules
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    NativeModules: {
      ...RN.NativeModules,
      RNVideo: {
        Constants: {},
      },
      TouchID: {
        isSupported: jest.fn(() => Promise.resolve(true)),
        authenticate: jest.fn(() => Promise.resolve(true)),
      },
      ReactNativeBiometrics: {
        isSensorAvailable: jest.fn(() => Promise.resolve({ available: true })),
        simplePrompt: jest.fn(() => Promise.resolve({ success: true })),
      },
    },
    Platform: {
      ...RN.Platform,
      OS: 'ios',
      Version: '14.0',
    },
    Dimensions: {
      get: jest.fn(() => ({ width: 375, height: 812 })),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    },
  };
});

// Mock React Navigation
jest.mock('@react-navigation/native', () => ({
  useNavigation: () => ({
    navigate: jest.fn(),
    goBack: jest.fn(),
    push: jest.fn(),
    pop: jest.fn(),
    replace: jest.fn(),
    reset: jest.fn(),
  }),
  useRoute: () => ({
    params: {},
  }),
  useFocusEffect: jest.fn(),
  NavigationContainer: ({ children }) => children,
}));

jest.mock('@react-navigation/stack', () => ({
  createStackNavigator: () => ({
    Navigator: ({ children }) => children,
    Screen: ({ children }) => children,
  }),
}));

jest.mock('@react-navigation/bottom-tabs', () => ({
  createBottomTabNavigator: () => ({
    Navigator: ({ children }) => children,
    Screen: ({ children }) => children,
  }),
}));

// Mock Redux
jest.mock('react-redux', () => ({
  useSelector: jest.fn(),
  useDispatch: () => jest.fn(),
  Provider: ({ children }) => children,
}));

// Mock Firebase
jest.mock('@react-native-firebase/messaging', () => ({
  __esModule: true,
  default: () => ({
    requestPermission: jest.fn(() => Promise.resolve(true)),
    getToken: jest.fn(() => Promise.resolve('mock-token')),
    onMessage: jest.fn(),
    onNotificationOpenedApp: jest.fn(),
    getInitialNotification: jest.fn(() => Promise.resolve(null)),
    setBackgroundMessageHandler: jest.fn(),
    onTokenRefresh: jest.fn(),
  }),
}));

jest.mock('@react-native-firebase/auth', () => ({
  __esModule: true,
  default: () => ({
    signInWithEmailAndPassword: jest.fn(() => 
      Promise.resolve({ user: { uid: 'mock-uid', email: 'test@example.com' } })
    ),
    signOut: jest.fn(() => Promise.resolve()),
    onAuthStateChanged: jest.fn(),
  }),
}));

jest.mock('@react-native-firebase/firestore', () => ({
  __esModule: true,
  default: () => ({
    collection: jest.fn(() => ({
      doc: jest.fn(() => ({
        set: jest.fn(() => Promise.resolve()),
        get: jest.fn(() => Promise.resolve({ exists: true, data: () => ({}) })),
        update: jest.fn(() => Promise.resolve()),
      })),
    })),
  }),
}));

jest.mock('@react-native-firebase/analytics', () => ({
  __esModule: true,
  default: () => ({
    logEvent: jest.fn(() => Promise.resolve()),
    setUserProperty: jest.fn(() => Promise.resolve()),
    setAnalyticsCollectionEnabled: jest.fn(() => Promise.resolve()),
  }),
}));

jest.mock('@react-native-firebase/crashlytics', () => ({
  __esModule: true,
  default: () => ({
    recordError: jest.fn(() => Promise.resolve()),
    log: jest.fn(() => Promise.resolve()),
    setCrashlyticsCollectionEnabled: jest.fn(() => Promise.resolve()),
  }),
}));

// Mock Video Player
jest.mock('react-native-video', () => 'Video');

// Mock Biometrics
jest.mock('react-native-biometrics', () => ({
  TouchID: {
    isSupported: jest.fn(() => Promise.resolve(true)),
    authenticate: jest.fn(() => Promise.resolve({ success: true })),
  },
  BiometryTypes: {
    TouchID: 'TouchID',
    FaceID: 'FaceID',
    Biometrics: 'Biometrics',
  },
}));

// Mock Push Notifications
jest.mock('react-native-push-notification', () => ({
  configure: jest.fn(),
  requestPermissions: jest.fn(),
  localNotification: jest.fn(),
  cancelAllLocalNotifications: jest.fn(),
}));

jest.mock('@react-native-notifee/react-native', () => ({
  displayNotification: jest.fn(),
  requestPermission: jest.fn(() => Promise.resolve(1)),
  createChannel: jest.fn(),
  cancelNotification: jest.fn(),
}));

// Mock Network Info
jest.mock('@react-native-netinfo/netinfo', () => ({
  fetch: jest.fn(() => 
    Promise.resolve({
      isConnected: true,
      type: 'wifi',
      isInternetReachable: true,
    })
  ),
  addEventListener: jest.fn(() => jest.fn()),
}));

// Mock Permissions
jest.mock('react-native-permissions', () => ({
  check: jest.fn(() => Promise.resolve('granted')),
  request: jest.fn(() => Promise.resolve('granted')),
  PERMISSIONS: {
    IOS: {
      CAMERA: 'ios.permission.CAMERA',
      MICROPHONE: 'ios.permission.MICROPHONE',
      PHOTO_LIBRARY: 'ios.permission.PHOTO_LIBRARY',
      FACE_ID: 'ios.permission.FACE_ID',
    },
    ANDROID: {
      CAMERA: 'android.permission.CAMERA',
      RECORD_AUDIO: 'android.permission.RECORD_AUDIO',
      READ_EXTERNAL_STORAGE: 'android.permission.READ_EXTERNAL_STORAGE',
      WRITE_EXTERNAL_STORAGE: 'android.permission.WRITE_EXTERNAL_STORAGE',
      USE_FINGERPRINT: 'android.permission.USE_FINGERPRINT',
      USE_BIOMETRIC: 'android.permission.USE_BIOMETRIC',
    },
  },
  RESULTS: {
    GRANTED: 'granted',
    DENIED: 'denied',
    BLOCKED: 'blocked',
    UNAVAILABLE: 'unavailable',
  },
}));

// Mock Vector Icons
jest.mock('react-native-vector-icons/MaterialIcons', () => 'Icon');
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');
jest.mock('react-native-vector-icons/FontAwesome', () => 'Icon');

// Mock Gesture Handler
jest.mock('react-native-gesture-handler', () => ({
  GestureHandlerRootView: ({ children }) => children,
  PanGestureHandler: ({ children }) => children,
  TapGestureHandler: ({ children }) => children,
  State: {},
  Directions: {},
}));

// Mock Reanimated
jest.mock('react-native-reanimated', () => ({
  Value: jest.fn(() => ({
    setValue: jest.fn(),
    addListener: jest.fn(),
    removeListener: jest.fn(),
  })),
  timing: jest.fn(),
  spring: jest.fn(),
  decay: jest.fn(),
  sequence: jest.fn(),
  parallel: jest.fn(),
  delay: jest.fn(),
  loop: jest.fn(),
  event: jest.fn(),
  createAnimatedComponent: jest.fn(),
  interpolate: jest.fn(),
  Extrapolate: { CLAMP: 'clamp' },
  Easing: { out: jest.fn(), ease: jest.fn() },
}));

// Mock WebSocket
global.WebSocket = class WebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 1; // OPEN
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 100);
  }

  send = jest.fn();
  close = jest.fn();
  addEventListener = jest.fn();
  removeEventListener = jest.fn();
};

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
  })
);

// Console.warn mock
const originalWarn = console.warn;
beforeAll(() => {
  console.warn = jest.fn();
});

afterAll(() => {
  console.warn = originalWarn;
});

// Cleanup after each test
afterEach(() => {
  jest.clearAllMocks();
});
