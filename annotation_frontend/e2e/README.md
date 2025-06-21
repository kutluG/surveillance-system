# E2E Testing with Playwright

This directory contains end-to-end (E2E) tests for the annotation workflow using [Playwright](https://playwright.dev/). The tests automate the full annotation flow: loading the annotation page, fetching examples, annotating images, submitting annotations, and verifying server-side records.

## 📁 Structure

```
e2e/
├── annotation.spec.ts    # Main E2E test file with annotation workflow tests
├── global-setup.ts       # Global setup for E2E test environment
├── global-teardown.ts    # Global teardown and cleanup
└── README.md            # This file

playwright.config.ts     # Playwright configuration
run-e2e-tests.sh        # Linux/Mac test runner script
run-e2e-tests.ps1       # Windows PowerShell test runner script
```

## 🚀 Quick Start

### Prerequisites

1. **Node.js** (v18 or higher)
2. **Python** (v3.11 or higher)
3. **Database services** (PostgreSQL, Redis, Kafka) - either locally or via Docker

### Install Dependencies

```bash
# Install Node.js dependencies (includes Playwright)
npm ci

# Install Playwright browsers
npx playwright install --with-deps
```

### Run Tests

#### Option 1: Using Scripts (Recommended)

**Linux/Mac:**
```bash
# Run basic tests
./run-e2e-tests.sh

# Run with specific browser
./run-e2e-tests.sh --browser firefox

# Run in headed mode (visible browser)
./run-e2e-tests.sh --headed

# Run using Docker for services
./run-e2e-tests.sh --docker

# Run in debug mode
./run-e2e-tests.sh --debug
```

**Windows PowerShell:**
```powershell
# Run basic tests
.\run-e2e-tests.ps1

# Run with specific browser
.\run-e2e-tests.ps1 -Browser firefox

# Run in headed mode
.\run-e2e-tests.ps1 -Headed

# Run using Docker for services
.\run-e2e-tests.ps1 -Docker

# Run in debug mode
.\run-e2e-tests.ps1 -Debug
```

#### Option 2: Direct Playwright Commands

```bash
# Run all tests
npx playwright test

# Run specific browser
npx playwright test --project=chromium

# Run in headed mode
npx playwright test --headed

# Run in debug mode
npx playwright test --debug

# Show test report
npx playwright show-report
```

## 🧪 Test Scenarios

The E2E tests cover the following scenarios:

### 1. **Annotation Interface Loading**
- ✅ Loads the annotation page successfully
- ✅ Verifies all UI components are present
- ✅ Checks canvas initialization

### 2. **Example Management**
- ✅ Fetches examples from the API
- ✅ Displays examples in the UI
- ✅ Handles empty example lists
- ✅ Manages example selection

### 3. **Image Annotation**
- ✅ Draws bounding boxes on canvas
- ✅ Selects annotation labels
- ✅ Validates annotation data
- ✅ Handles multiple annotations

### 4. **Form Submission**
- ✅ Submits annotations via API
- ✅ Validates request payload
- ✅ Handles success responses
- ✅ Shows success feedback

### 5. **Error Handling**
- ✅ Handles API failures gracefully
- ✅ Shows error messages
- ✅ Validates error states

### 6. **User Interactions**
- ✅ Skip functionality
- ✅ Correction workflows
- ✅ Form validation
- ✅ UI feedback

### 7. **Responsive Design**
- ✅ Mobile layout testing
- ✅ Touch interactions
- ✅ Cross-browser compatibility

## 🔧 Configuration

### Playwright Configuration (`playwright.config.ts`)

Key configuration options:

```typescript
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  use: {
    baseURL: 'http://localhost:8001',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } },
  ],
  
  webServer: {
    command: 'python main.py',
    url: 'http://localhost:8001',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:pass@localhost:5432/events_db

# Redis connection
REDIS_URL=redis://localhost:6379

# Kafka connection
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Application settings
PORT=8001
ENV=test
```

## 🐳 Docker Setup

For isolated testing, use the provided Docker Compose configuration:

```bash
# Start test environment
docker-compose -f ../docker-compose.e2e.yml up -d

# Run tests
npx playwright test

# Cleanup
docker-compose -f ../docker-compose.e2e.yml down -v
```

## 📊 Test Reports

Playwright generates comprehensive test reports:

### HTML Report
```bash
npx playwright show-report
```
- Interactive test results
- Screenshots and videos
- Network activity logs
- Performance metrics

### JUnit Report
- Located at `test-results/e2e-results.xml`
- Compatible with CI/CD systems
- Structured test results

### JSON Report
- Located at `test-results/e2e-results.json`
- Programmatic test data
- Custom report generation

## 🔍 Debugging

### Debug Mode
```bash
# Open Playwright Inspector
npx playwright test --debug

# Run specific test in debug mode
npx playwright test annotation.spec.ts --debug
```

### Trace Viewer
```bash
# View traces for failed tests
npx playwright show-trace test-results/trace.zip
```

### Screenshots and Videos
- Screenshots: `test-results/screenshots/`
- Videos: `test-results/videos/`
- Only captured on failures (configurable)

## 🚦 CI/CD Integration

### GitHub Actions

The tests are integrated into the CI pipeline:

```yaml
# .github/workflows/ci.yml
annotation-e2e-tests:
  runs-on: ubuntu-latest
  services:
    postgres: # PostgreSQL service
    redis: # Redis service
    kafka: # Kafka service
  steps:
    - uses: actions/checkout@v4
    - name: Setup Node.js
      uses: actions/setup-node@v4
    - name: Install dependencies
      run: npm ci
    - name: Install Playwright browsers
      run: npx playwright install --with-deps chromium
    - name: Run E2E tests
      run: npx playwright test --project=chromium
```

### Standalone E2E Workflow

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on:
  workflow_dispatch:
    inputs:
      browser:
        type: choice
        options: [chromium, firefox, webkit, all]
      headed:
        type: boolean
```

## 🛠️ Development

### Adding New Tests

1. Create test files in the `e2e/` directory
2. Use the existing `annotation.spec.ts` as a template
3. Follow Playwright best practices:
   - Use page object patterns
   - Mock external dependencies
   - Assert on meaningful user outcomes
   - Keep tests independent

### Network Mocking

```typescript
// Mock API responses
await page.route('**/api/v1/examples', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(mockData)
  });
});

// Intercept and validate requests
await page.route('**/api/v1/examples/*/label', route => {
  const request = route.request();
  const payload = JSON.parse(request.postData());
  
  // Validate payload
  expect(payload).toMatchObject({
    bbox: expect.arrayContaining([expect.any(Number)]),
    label: expect.any(String)
  });
  
  route.fulfill({ status: 200, body: '{"success": true}' });
});
```

### Custom Fixtures

```typescript
// Create reusable test fixtures
export const test = base.extend<{
  annotationPage: AnnotationPage;
}>({
  annotationPage: async ({ page }, use) => {
    const annotationPage = new AnnotationPage(page);
    await annotationPage.goto();
    await use(annotationPage);
  },
});
```

## 📋 Best Practices

### 1. **Test Independence**
- Each test should be self-contained
- No shared state between tests
- Clean setup and teardown

### 2. **Reliable Selectors**
- Use `data-testid` attributes
- Prefer semantic selectors
- Avoid brittle CSS selectors

### 3. **Network Handling**
- Mock external API calls
- Test only what you control
- Use network interception for validation

### 4. **Assertions**
- Assert on user-visible outcomes
- Use meaningful error messages
- Test both positive and negative cases

### 5. **Performance**
- Minimize test execution time
- Use parallel execution
- Optimize browser startup

## 🐛 Troubleshooting

### Common Issues

**Tests failing with timeout:**
```bash
# Increase timeout in playwright.config.ts
timeout: 60000, // 60 seconds
```

**Browser not starting:**
```bash
# Reinstall browsers
npx playwright install --force
```

**Services not ready:**
```bash
# Check service health
docker-compose -f ../docker-compose.e2e.yml ps
```

**Network issues:**
```bash
# Check port availability
netstat -tulpn | grep :8001
```

### Logs and Debugging

```bash
# Enable debug logging
DEBUG=pw:api npx playwright test

# Save console logs
npx playwright test --reporter=line,html

# Capture full page screenshots
npx playwright test --screenshot=on
```

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Test Configuration](https://playwright.dev/docs/test-configuration)
- [Network Mocking](https://playwright.dev/docs/network)
- [CI/CD Integration](https://playwright.dev/docs/ci-intro)

## 🤝 Contributing

1. Follow the existing test patterns
2. Add tests for new features
3. Update documentation
4. Ensure tests pass in CI
5. Add meaningful test descriptions

## 📄 License

This project is part of the surveillance system and follows the same license terms.
