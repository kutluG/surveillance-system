import { chromium, type FullConfig } from '@playwright/test';

/**
 * Global setup for E2E tests
 * Sets up the test environment before all tests run
 */
async function globalSetup(config: FullConfig) {
  console.log('🔧 Setting up E2E test environment...');
  
  // Set environment variables for test mode
  process.env.TEST_MODE = 'true';
  process.env.DATABASE_URL = 'sqlite:///tmp/test_annotation.db';
  process.env.KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092';
  
  // Wait for services to be ready
  await waitForServices();
  
  // Initialize test data if needed
  await initializeTestData();
  
  console.log('✅ E2E test environment setup complete');
}

/**
 * Wait for required services to be available
 */
async function waitForServices() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  console.log('⏳ Waiting for FastAPI server to be ready...');
  
  let retries = 0;
  const maxRetries = 30;
  
  while (retries < maxRetries) {
    try {
      const response = await page.goto('http://localhost:8001/health', {
        waitUntil: 'networkidle',
        timeout: 5000
      });
      
      if (response && response.status() === 200) {
        console.log('✅ FastAPI server is ready');
        break;
      }
    } catch (error) {
      retries++;
      if (retries >= maxRetries) {
        throw new Error(`FastAPI server not ready after ${maxRetries} attempts`);
      }
      console.log(`⏳ Waiting for FastAPI server... (attempt ${retries}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  await browser.close();
}

/**
 * Initialize test data for annotation testing
 */
async function initializeTestData() {
  console.log('📝 Initializing test data...');
  
  // You can add test data initialization here
  // For example, creating test examples in the database
  
  console.log('✅ Test data initialized');
}

export default globalSetup;
