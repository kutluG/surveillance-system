const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://facebook.github.io/metro/docs/configuration
 *
 * @type {import('metro-config').MetroConfig}
 */
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://facebook.github.io/metro/docs/configuration
 *
 * @type {import('metro-config').MetroConfig}
 */
const config = {
  resolver: {
    alias: {
      '@': './src',
      '@components': './src/components',
      '@screens': './src/screens',
      '@services': './src/services',
      '@utils': './src/utils',
      '@constants': './src/constants',
      '@store': './src/store',
      '@contexts': './src/contexts',
      '@navigation': './src/navigation',
    },
    assetExts: [
      // Image formats
      'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg',
      // Video formats
      'mp4', 'mov', 'avi', 'mkv', 'webm',
      // Audio formats
      'mp3', 'wav', 'aac', 'm4a',
      // Font formats
      'ttf', 'otf', 'woff', 'woff2',
      // Other formats
      'pdf', 'zip', 'json',
    ],
    sourceExts: ['js', 'jsx', 'ts', 'tsx', 'json'],
  },
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true,
      },
    }),
    babelTransformerPath: require.resolve('react-native-svg-transformer'),
    assetPlugins: ['react-native-svg-transformer'],
  },
  serializer: {
    getModulesRunBeforeMain: () => [
      require.resolve('react-native/Libraries/Core/InitializeCore'),
    ],
  },
  watchFolders: [],
  server: {
    port: 8081,
  },
  resetCache: false,
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
