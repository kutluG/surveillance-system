const Sequencer = require('@jest/test-sequencer').default;

class E2ETestSequencer extends Sequencer {
  /**
   * Sort test files in a specific order for E2E tests
   * Authentication tests should run first, then core functionality
   */
  sort(tests) {
    // Define the order of test execution
    const testOrder = [
      'authentication',
      'dashboard', 
      'cameras',
      'alerts',
      'settings',
      'network',
      'production',
      'performance'
    ];
    
    const sortedTests = [];
    
    // Sort tests based on predefined order
    testOrder.forEach(category => {
      const categoryTests = tests.filter(test => 
        test.path.includes(category) || test.path.includes(category.toLowerCase())
      );
      sortedTests.push(...categoryTests);
    });
    
    // Add any remaining tests that don't match the categories
    const remainingTests = tests.filter(test => 
      !sortedTests.some(sorted => sorted.path === test.path)
    );
    sortedTests.push(...remainingTests);
    
    return sortedTests;
  }
}

module.exports = E2ETestSequencer;
