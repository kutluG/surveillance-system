const detox = require('detox');

module.exports = async () => {
  console.log('🧹 Tearing down E2E test environment...');
  
  // Clean up Detox
  await detox.cleanup();
  
  console.log('✅ E2E test environment teardown complete');
};
