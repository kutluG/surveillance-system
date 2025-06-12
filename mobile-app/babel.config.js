module.exports = {
  presets: ['@react-native/babel-preset'],
  plugins: [
    'react-native-reanimated/plugin',
    [
      'module-resolver',
      {
        root: ['./src'],
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
      },
    ],
  ],
};
