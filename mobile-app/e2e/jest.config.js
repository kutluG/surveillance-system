{
  "preset": "react-native",
  "testEnvironment": "node",
  "testRunner": "jest-circus/runner",
  "testTimeout": 120000,
  "testRegex": "\\.e2e\\.(js|ts)$",
  "verbose": true,
  "setupFilesAfterEnv": ["<rootDir>/init.js"],
  "globalSetup": "<rootDir>/global-setup.js",
  "globalTeardown": "<rootDir>/global-teardown.js",
  "testMatch": [
    "<rootDir>/**/*.e2e.{js,ts}"
  ],
  "transform": {
    "^.+\\.(js|ts)$": "babel-jest"
  },
  "moduleFileExtensions": [
    "ts",
    "tsx", 
    "js",
    "jsx",
    "json",
    "node"
  ],
  "transformIgnorePatterns": [
    "node_modules/(?!(react-native|@react-native|detox)/)"
  ],
  "reporters": [
    "default",
    ["jest-junit", {
      "outputDirectory": "e2e/reports",
      "outputName": "e2e-test-results.xml"
    }]
  ],
  "collectCoverage": false,
  "testSequencer": "<rootDir>/test-sequencer.js"
}
