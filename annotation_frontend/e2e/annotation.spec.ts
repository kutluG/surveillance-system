import { test, expect, type Page } from '@playwright/test';

/**
 * E2E Tests for Annotation Workflow
 * Tests the complete annotation flow from loading examples to submitting annotations
 */

test.describe('Annotation Workflow E2E', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to annotation page
    await page.goto('/annotation');
    
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle');
    
    // Verify page title
    await expect(page).toHaveTitle(/Annotation Interface/);
  });

  test('should load annotation interface with all components', async ({ page }) => {
    // Verify main components are present
    await expect(page.locator('#examples-list')).toBeVisible();
    await expect(page.locator('#pending-count')).toBeVisible();
    await expect(page.locator('#annotation-canvas')).toBeVisible();
    await expect(page.locator('#submit-button')).toBeVisible();
    await expect(page.locator('#skip-button')).toBeVisible();
    
    // Verify form elements
    await expect(page.locator('#annotator-id')).toBeVisible();
    await expect(page.locator('#quality-score')).toBeVisible();
    await expect(page.locator('#notes')).toBeVisible();
  });

  test('should fetch and display examples on page load', async ({ page }) => {
    // Mock the API response for examples
    await page.route('**/api/v1/examples', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          examples: [
            {
              event_id: 'test-example-1',
              camera_id: 'cam-001',
              timestamp: '2025-06-16T10:00:00Z',
              reason: 'Low confidence detection',
              confidence_scores: { person: 0.3, vehicle: 0.1 },
              detections: [
                {
                  bbox: [100, 100, 200, 200],
                  class_name: 'person',
                  confidence: 0.3
                }
              ]
            },
            {
              event_id: 'test-example-2', 
              camera_id: 'cam-002',
              timestamp: '2025-06-16T11:00:00Z',
              reason: 'Multiple class detection',
              confidence_scores: { person: 0.5, vehicle: 0.4 }
            }
          ],
          total: 2
        })
      });
    });

    // Refresh the page to trigger API call
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify pending count is updated
    await expect(page.locator('#pending-count')).toHaveText('2');

    // Verify examples are displayed
    const exampleCards = page.locator('.example-card');
    await expect(exampleCards).toHaveCount(2);
    
    // Verify first example details
    const firstExample = exampleCards.first();
    await expect(firstExample).toContainText('cam-001');
    await expect(firstExample).toContainText('Low confidence detection');
  });

  test('should load example details when clicked', async ({ page }) => {
    // Mock examples list
    await page.route('**/api/v1/examples', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          examples: [{
            event_id: 'test-example-1',
            camera_id: 'cam-001',
            timestamp: '2025-06-16T10:00:00Z',
            reason: 'Low confidence detection'
          }],
          total: 1
        })
      });
    });

    // Mock individual example details
    await page.route('**/api/v1/examples/test-example-1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          event_id: 'test-example-1',
          camera_id: 'cam-001',
          timestamp: '2025-06-16T10:00:00Z',
          detections: [
            {
              bbox: [150, 150, 250, 250],
              class_name: 'person',
              confidence: 0.75
            },
            {
              bbox: [300, 100, 400, 180],
              class_name: 'vehicle',
              confidence: 0.65
            }
          ]
        })
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Click on the first example
    await page.locator('.example-card').first().click();
    
    // Wait for example details to load
    await page.waitForTimeout(1000);

    // Verify annotation panel is shown
    await expect(page.locator('#annotation-panel')).toBeVisible();
    
    // Verify example title is updated
    const exampleTitle = page.locator('#example-title');
    await expect(exampleTitle).toContainText('cam-001');
    await expect(exampleTitle).toContainText('2025-06-16T10:00:00Z');

    // Verify detections are displayed
    const detectionItems = page.locator('.detection-item');
    await expect(detectionItems).toHaveCount(2);
  });

  test('should submit annotation with form data', async ({ page }) => {
    // Set up mocks
    await setupExampleMocks(page);

    // Track annotation submission
    let submittedData: any = null;
    await page.route('**/api/v1/examples/test-example-1/label', async route => {
      submittedData = await route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success', event_id: 'test-example-1' })
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Click on example to load it
    await page.locator('.example-card').first().click();
    await page.waitForTimeout(1000);

    // Fill in annotation form
    await page.locator('#annotator-id').fill('test-annotator-e2e');
    await page.locator('#quality-score').fill('0.8');
    await page.locator('#notes').fill('E2E test annotation notes');

    // Submit annotation
    await page.locator('#submit-button').click();

    // Wait for submission to complete
    await page.waitForTimeout(1000);

    // Verify submission data
    expect(submittedData).toBeTruthy();
    expect(submittedData.annotator_id).toBe('test-annotator-e2e');
    expect(submittedData.quality_score).toBe(0.8);
    expect(submittedData.notes).toBe('E2E test annotation notes');
    expect(submittedData.corrected_detections).toBeInstanceOf(Array);

    // Verify success message is shown
    const successAlert = page.locator('.alert-success');
    await expect(successAlert).toBeVisible();
    await expect(successAlert).toContainText('Annotation submitted successfully');
  });

  test('should validate required fields before submission', async ({ page }) => {
    // Set up mocks
    await setupExampleMocks(page);

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Click on example to load it
    await page.locator('.example-card').first().click();
    await page.waitForTimeout(1000);

    // Try to submit without annotator ID
    await page.locator('#submit-button').click();

    // Verify error message is shown
    const errorAlert = page.locator('.alert-danger');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Please enter your annotator ID');
  });

  test('should skip example when skip button is clicked', async ({ page }) => {
    // Set up mocks
    await setupExampleMocks(page);

    // Track skip request
    let skippedExampleId: string | null = null;
    await page.route('**/api/v1/examples/test-example-1', async route => {
      if (route.request().method() === 'DELETE') {
        skippedExampleId = 'test-example-1';
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'skipped', event_id: 'test-example-1' })
        });
      }
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Click on example to load it
    await page.locator('.example-card').first().click();
    await page.waitForTimeout(1000);

    // Mock the confirmation dialog
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Are you sure you want to skip');
      await dialog.accept();
    });

    // Click skip button
    await page.locator('#skip-button').click();

    // Wait for skip to complete
    await page.waitForTimeout(1000);

    // Verify skip request was made
    expect(skippedExampleId).toBe('test-example-1');
  });

  test('should handle detection corrections', async ({ page }) => {
    // Set up mocks
    await setupExampleMocks(page);

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Click on example to load it
    await page.locator('.example-card').first().click();
    await page.waitForTimeout(1000);

    // Verify detection correction controls are present
    const detectionItems = page.locator('.detection-item');
    await expect(detectionItems).toHaveCount(2);

    // Find and interact with correctness checkboxes
    const correctnessCheckboxes = page.locator('input[type="checkbox"]');
    if (await correctnessCheckboxes.count() > 0) {
      // Toggle first detection's correctness
      await correctnessCheckboxes.first().click();
    }

    // Find and interact with class selection dropdowns
    const classSelects = page.locator('select.class-select');
    if (await classSelects.count() > 0) {
      // Change class of first detection
      await classSelects.first().selectOption('vehicle');
    }

    // Fill form and submit
    await page.locator('#annotator-id').fill('test-annotator-e2e');
    
    // Track annotation submission to verify corrections
    let submittedData: any = null;
    await page.route('**/api/v1/examples/test-example-1/label', async route => {
      submittedData = await route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' })
      });
    });

    await page.locator('#submit-button').click();
    await page.waitForTimeout(1000);

    // Verify corrected detections were submitted
    expect(submittedData).toBeTruthy();
    expect(submittedData.corrected_detections).toBeInstanceOf(Array);
    expect(submittedData.corrected_detections.length).toBeGreaterThan(0);
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error for examples
    await page.route('**/api/v1/examples', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify error message is displayed
    const errorAlert = page.locator('.alert-danger');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Failed to load examples');
  });

  test('should maintain responsive design on mobile devices', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Set up mocks
    await setupExampleMocks(page);

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify mobile layout
    await expect(page.locator('#examples-list')).toBeVisible();
    await expect(page.locator('#annotation-canvas')).toBeVisible();

    // Verify responsive navigation
    const exampleCards = page.locator('.example-card');
    await expect(exampleCards).toHaveCount(1);

    // Test mobile interaction
    await exampleCards.first().click();
    await page.waitForTimeout(1000);

    // Verify annotation panel works on mobile
    await expect(page.locator('#annotation-panel')).toBeVisible();
  });
});

/**
 * Helper function to set up common example mocks
 */
async function setupExampleMocks(page: Page) {
  // Mock examples list
  await page.route('**/api/v1/examples', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        examples: [{
          event_id: 'test-example-1',
          camera_id: 'cam-001',
          timestamp: '2025-06-16T10:00:00Z',
          reason: 'Low confidence detection'
        }],
        total: 1
      })
    });
  });

  // Mock individual example details
  await page.route('**/api/v1/examples/test-example-1', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        event_id: 'test-example-1',
        camera_id: 'cam-001',
        timestamp: '2025-06-16T10:00:00Z',
        detections: [
          {
            bbox: [150, 150, 250, 250],
            class_name: 'person',
            confidence: 0.75
          },
          {
            bbox: [300, 100, 400, 180],
            class_name: 'vehicle',
            confidence: 0.65
          }
        ]
      })
    });
  });
}
