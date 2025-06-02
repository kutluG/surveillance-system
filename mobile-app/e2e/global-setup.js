const detox = require('detox');

module.exports = async () => {
  // Set up global environment for E2E tests
  console.log('🔧 Setting up E2E test environment...');
  
  // Initialize Detox
  const config = require('../package.json').detox;
  await detox.init(config, { initGlobals: false });
  
  // Set global timeout for all E2E tests
  jest.setTimeout(300000); // 5 minutes for long-running E2E tests
  
  console.log('✅ E2E test environment setup complete');
};
