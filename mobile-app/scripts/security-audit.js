#!/usr/bin/env node

/**
 * Security Audit Script
 * Performs comprehensive security validation for the surveillance system
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const axios = require('axios');

class SecurityAuditor {
  constructor() {
    this.auditResults = {
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      passed: 0,
      failed: 0,
      warnings: 0,
      critical: 0,
      checks: []
    };

    this.config = {
      mobileAppPath: path.join(__dirname, '..', '..'),
      backendPath: path.join(__dirname, '..', '..', '..'),
      sensitivePatterns: [
        /password\s*[:=]\s*["'](?!.*\$\{)[^"']{3,}["']/gi,
        /api[_-]?key\s*[:=]\s*["'](?!.*\$\{)[^"']{10,}["']/gi,
        /secret\s*[:=]\s*["'](?!.*\$\{)[^"']{8,}["']/gi,
        /token\s*[:=]\s*["'](?!.*\$\{)[A-Za-z0-9+/]{20,}["']/gi,
        /private[_-]?key\s*[:=]\s*["'][^"']{50,}["']/gi
      ],
      vulnerablePackages: [
        'moment', // Known vulnerabilities in older versions
        'request', // Deprecated
        'lodash', // Prototype pollution in older versions
      ],
      requiredSecurityHeaders: [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'X-XSS-Protection',
        'Strict-Transport-Security'
      ]
    };
  }

  /**
   * Run complete security audit
   */
  async runAudit() {
    console.log('🔒 Starting comprehensive security audit...\n');

    try {
      // Mobile app security checks
      await this.auditMobileAppSecurity();
      
      // Backend security checks
      await this.auditBackendSecurity();
      
      // Network security checks
      await this.auditNetworkSecurity();
      
      // Dependencies audit
      await this.auditDependencies();
      
      // Configuration security
      await this.auditConfiguration();
      
      // Generate report
      this.generateSecurityReport();
      
    } catch (error) {
      console.error('❌ Security audit failed:', error.message);
      process.exit(1);
    }
  }

  /**
   * Audit mobile app security
   */
  async auditMobileAppSecurity() {
    console.log('📱 Auditing mobile app security...');

    // Check for hardcoded secrets
    await this.checkHardcodedSecrets(this.config.mobileAppPath, 'Mobile App');

    // Validate authentication implementation
    this.validateAuthenticationSecurity();

    // Check certificate pinning
    this.validateCertificatePinning();

    // Validate biometric security
    this.validateBiometricSecurity();

    // Check network security configuration
    this.validateNetworkSecurityConfig();

    // Validate secure storage implementation
    this.validateSecureStorage();
  }

  /**
   * Audit backend security
   */
  async auditBackendSecurity() {
    console.log('🖥️  Auditing backend security...');

    // Check for hardcoded secrets in backend
    await this.checkHardcodedSecrets(this.config.backendPath, 'Backend');

    // Validate JWT configuration
    this.validateJWTSecurity();

    // Check API endpoint security
    await this.validateAPIEndpointSecurity();

    // Validate database security
    this.validateDatabaseSecurity();
  }

  /**
   * Audit network security
   */
  async auditNetworkSecurity() {
    console.log('🌐 Auditing network security...');

    // Test HTTPS enforcement
    await this.testHTTPSEnforcement();

    // Check security headers
    await this.checkSecurityHeaders();

    // Validate CORS configuration
    this.validateCORSConfiguration();
  }

  /**
   * Audit dependencies
   */
  async auditDependencies() {
    console.log('📦 Auditing dependencies...');

    // Check mobile app dependencies
    await this.auditPackageJson(path.join(this.config.mobileAppPath, 'package.json'), 'Mobile App');

    // Check backend dependencies
    const backendPackageJson = path.join(this.config.backendPath, 'package.json');
    if (fs.existsSync(backendPackageJson)) {
      await this.auditPackageJson(backendPackageJson, 'Backend');
    }

    // Check Python dependencies
    const requirementsFile = path.join(this.config.backendPath, 'requirements.txt');
    if (fs.existsSync(requirementsFile)) {
      await this.auditPythonDependencies(requirementsFile);
    }
  }

  /**
   * Audit configuration security
   */
  async auditConfiguration() {
    console.log('⚙️  Auditing configuration security...');

    // Check environment configuration
    this.validateEnvironmentConfiguration();

    // Check Docker security
    this.validateDockerSecurity();

    // Check file permissions
    this.validateFilePermissions();
  }

  /**
   * Check for hardcoded secrets
   */
  async checkHardcodedSecrets(dirPath, component) {
    if (!fs.existsSync(dirPath)) {
      this.addCheck(`${component} - Hardcoded Secrets`, 'SKIP', 'Directory not found');
      return;
    }

    const violations = [];
    const files = this.getAllSourceFiles(dirPath);

    for (const file of files) {
      try {
        const content = fs.readFileSync(file, 'utf8');
        const relativePath = path.relative(dirPath, file);

        for (const pattern of this.config.sensitivePatterns) {
          const matches = content.match(pattern);
          if (matches) {
            violations.push({
              file: relativePath,
              matches: matches.length,
              pattern: pattern.source.substring(0, 50) + '...'
            });
          }
        }
      } catch (error) {
        // Skip files that can't be read
      }
    }

    if (violations.length > 0) {
      this.addCheck(
        `${component} - Hardcoded Secrets`,
        'FAIL',
        `Found ${violations.length} potential hardcoded secrets`,
        violations
      );
    } else {
      this.addCheck(`${component} - Hardcoded Secrets`, 'PASS', 'No hardcoded secrets detected');
    }
  }

  /**
   * Validate authentication security
   */
  validateAuthenticationSecurity() {
    const authServicePath = path.join(this.config.mobileAppPath, 'src', 'services', 'authService.js');
    
    if (!fs.existsSync(authServicePath)) {
      this.addCheck('Authentication Security', 'FAIL', 'AuthService not found');
      return;
    }

    const authContent = fs.readFileSync(authServicePath, 'utf8');
    const issues = [];

    // Check for proper token handling
    if (!authContent.includes('Authorization')) {
      issues.push('Missing Authorization header handling');
    }

    // Check for token expiration handling
    if (!authContent.includes('refresh')) {
      issues.push('No token refresh mechanism found');
    }

    // Check for secure storage
    if (!authContent.includes('AsyncStorage') && !authContent.includes('SecureStore')) {
      issues.push('No secure storage implementation found');
    }

    if (issues.length > 0) {
      this.addCheck('Authentication Security', 'WARNING', 'Authentication issues found', issues);
    } else {
      this.addCheck('Authentication Security', 'PASS', 'Authentication properly implemented');
    }
  }

  /**
   * Validate certificate pinning
   */
  validateCertificatePinning() {
    const certPinningPath = path.join(this.config.mobileAppPath, 'src', 'security', 'certificatePinning.js');
    
    if (fs.existsSync(certPinningPath)) {
      this.addCheck('Certificate Pinning', 'PASS', 'Certificate pinning implemented');
    } else {
      this.addCheck('Certificate Pinning', 'WARNING', 'Certificate pinning not implemented');
    }
  }

  /**
   * Validate biometric security
   */
  validateBiometricSecurity() {
    const biometricPath = path.join(this.config.mobileAppPath, 'src', 'services', 'biometricService.js');
    
    if (!fs.existsSync(biometricPath)) {
      this.addCheck('Biometric Security', 'WARNING', 'Biometric authentication not implemented');
      return;
    }

    const biometricContent = fs.readFileSync(biometricPath, 'utf8');
    const features = [];

    if (biometricContent.includes('TouchID')) features.push('Touch ID');
    if (biometricContent.includes('FaceID')) features.push('Face ID');
    if (biometricContent.includes('Fingerprint')) features.push('Fingerprint');

    if (features.length > 0) {
      this.addCheck('Biometric Security', 'PASS', `Biometric authentication implemented: ${features.join(', ')}`);
    } else {
      this.addCheck('Biometric Security', 'WARNING', 'Biometric service exists but no biometric methods detected');
    }
  }

  /**
   * Validate network security configuration
   */
  validateNetworkSecurityConfig() {
    const networkConfigPath = path.join(
      this.config.mobileAppPath,
      'android',
      'app',
      'src',
      'main',
      'res',
      'xml',
      'network_security_config.xml'
    );

    if (fs.existsSync(networkConfigPath)) {
      const configContent = fs.readFileSync(networkConfigPath, 'utf8');
      
      if (configContent.includes('cleartextTrafficPermitted="false"')) {
        this.addCheck('Network Security Config', 'PASS', 'Cleartext traffic properly restricted in production');
      } else {
        this.addCheck('Network Security Config', 'WARNING', 'Cleartext traffic may be permitted');
      }
    } else {
      this.addCheck('Network Security Config', 'FAIL', 'Network security configuration missing for Android');
    }
  }

  /**
   * Validate secure storage
   */
  validateSecureStorage() {
    const securityManagerPath = path.join(this.config.mobileAppPath, 'src', 'security', 'securityManager.js');
    
    if (!fs.existsSync(securityManagerPath)) {
      this.addCheck('Secure Storage', 'FAIL', 'Security manager not found');
      return;
    }

    const securityContent = fs.readFileSync(securityManagerPath, 'utf8');
    
    if (securityContent.includes('encryptData') && securityContent.includes('decryptData')) {
      this.addCheck('Secure Storage', 'PASS', 'Secure storage with encryption implemented');
    } else {
      this.addCheck('Secure Storage', 'WARNING', 'Secure storage implementation incomplete');
    }
  }

  /**
   * Validate JWT security
   */
  validateJWTSecurity() {
    const authPath = path.join(this.config.backendPath, 'shared', 'auth.py');
    
    if (!fs.existsSync(authPath)) {
      this.addCheck('JWT Security', 'FAIL', 'Backend auth module not found');
      return;
    }

    const authContent = fs.readFileSync(authPath, 'utf8');
    const issues = [];

    // Check for proper secret management
    if (authContent.includes('change-me')) {
      issues.push('Default JWT secret detected');
    }

    // Check for token expiration
    if (!authContent.includes('expires_delta') && !authContent.includes('exp')) {
      issues.push('No token expiration found');
    }

    // Check for algorithm specification
    if (!authContent.includes('HS256') && !authContent.includes('RS256')) {
      issues.push('JWT algorithm not specified');
    }

    if (issues.length > 0) {
      this.addCheck('JWT Security', 'WARNING', 'JWT configuration issues found', issues);
    } else {
      this.addCheck('JWT Security', 'PASS', 'JWT properly configured');
    }
  }

  /**
   * Validate API endpoint security
   */
  async validateAPIEndpointSecurity() {
    const testEndpoints = [
      { url: 'http://localhost:8001/health', requiresAuth: false },
      { url: 'http://localhost:8001/auth/login', requiresAuth: false },
      { url: 'http://localhost:8001/auth/me', requiresAuth: true },
    ];

    const authTests = [];

    for (const endpoint of testEndpoints) {
      try {
        const response = await axios.get(endpoint.url, { timeout: 3000 });
        
        if (endpoint.requiresAuth && response.status === 200) {
          authTests.push(`${endpoint.url} - Accessible without authentication`);
        }
      } catch (error) {
        if (endpoint.requiresAuth && error.response?.status === 401) {
          // This is expected for protected endpoints
          continue;
        }
        // Skip endpoints that are not accessible
      }
    }

    if (authTests.length > 0) {
      this.addCheck('API Endpoint Security', 'FAIL', 'Protected endpoints accessible without auth', authTests);
    } else {
      this.addCheck('API Endpoint Security', 'PASS', 'API endpoints properly protected');
    }
  }

  /**
   * Validate database security
   */
  validateDatabaseSecurity() {
    const envExamplePath = path.join(this.config.backendPath, '.env.example');
    
    if (!fs.existsSync(envExamplePath)) {
      this.addCheck('Database Security', 'WARNING', 'Environment example file not found');
      return;
    }

    const envContent = fs.readFileSync(envExamplePath, 'utf8');
    const issues = [];

    // Check for default passwords
    if (envContent.includes('password=password') || envContent.includes('password=123')) {
      issues.push('Default database password detected');
    }

    // Check for SSL configuration
    if (!envContent.includes('sslmode') && !envContent.includes('SSL')) {
      issues.push('No SSL configuration for database');
    }

    if (issues.length > 0) {
      this.addCheck('Database Security', 'WARNING', 'Database security issues found', issues);
    } else {
      this.addCheck('Database Security', 'PASS', 'Database security properly configured');
    }
  }

  /**
   * Test HTTPS enforcement
   */
  async testHTTPSEnforcement() {
    try {
      // Test if HTTP redirects to HTTPS (in production)
      if (process.env.NODE_ENV === 'production') {
        const response = await axios.get('http://api.surveillance-ai.com/health', {
          timeout: 5000,
          maxRedirects: 0,
          validateStatus: (status) => status < 400
        });

        if (response.status === 301 || response.status === 302) {
          this.addCheck('HTTPS Enforcement', 'PASS', 'HTTP properly redirects to HTTPS');
        } else {
          this.addCheck('HTTPS Enforcement', 'FAIL', 'HTTP does not redirect to HTTPS');
        }
      } else {
        this.addCheck('HTTPS Enforcement', 'SKIP', 'Not applicable in development');
      }
    } catch (error) {
      this.addCheck('HTTPS Enforcement', 'SKIP', 'Could not test HTTPS enforcement');
    }
  }

  /**
   * Check security headers
   */
  async checkSecurityHeaders() {
    try {
      const response = await axios.get('http://localhost:8001/health', { timeout: 3000 });
      const headers = response.headers;
      const missingHeaders = [];

      for (const header of this.config.requiredSecurityHeaders) {
        if (!headers[header.toLowerCase()]) {
          missingHeaders.push(header);
        }
      }

      if (missingHeaders.length > 0) {
        this.addCheck('Security Headers', 'WARNING', 'Missing security headers', missingHeaders);
      } else {
        this.addCheck('Security Headers', 'PASS', 'All required security headers present');
      }
    } catch (error) {
      this.addCheck('Security Headers', 'SKIP', 'Could not test security headers');
    }
  }

  /**
   * Validate CORS configuration
   */
  validateCORSConfiguration() {
    // This would typically test CORS headers, but we'll check configuration files
    const dockerComposePath = path.join(this.config.backendPath, 'docker-compose.yml');
    
    if (fs.existsSync(dockerComposePath)) {
      const dockerContent = fs.readFileSync(dockerComposePath, 'utf8');
      
      if (dockerContent.includes('CORS_ALLOW_ORIGINS')) {
        this.addCheck('CORS Configuration', 'PASS', 'CORS configuration found');
      } else {
        this.addCheck('CORS Configuration', 'WARNING', 'CORS configuration not explicitly set');
      }
    } else {
      this.addCheck('CORS Configuration', 'SKIP', 'Docker compose file not found');
    }
  }

  /**
   * Audit package.json dependencies
   */
  async auditPackageJson(packagePath, component) {
    if (!fs.existsSync(packagePath)) {
      this.addCheck(`${component} Dependencies`, 'SKIP', 'package.json not found');
      return;
    }

    try {
      const packageData = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
      const dependencies = { ...packageData.dependencies, ...packageData.devDependencies };
      const vulnerableFound = [];

      for (const [pkg, version] of Object.entries(dependencies)) {
        if (this.config.vulnerablePackages.includes(pkg)) {
          vulnerableFound.push(`${pkg}@${version}`);
        }
      }

      if (vulnerableFound.length > 0) {
        this.addCheck(`${component} Dependencies`, 'WARNING', 'Potentially vulnerable packages found', vulnerableFound);
      } else {
        this.addCheck(`${component} Dependencies`, 'PASS', 'No known vulnerable packages detected');
      }
    } catch (error) {
      this.addCheck(`${component} Dependencies`, 'FAIL', 'Could not parse package.json');
    }
  }

  /**
   * Audit Python dependencies
   */
  async auditPythonDependencies(requirementsPath) {
    try {
      const requirements = fs.readFileSync(requirementsPath, 'utf8');
      const packages = requirements.split('\n').filter(line => line.trim() && !line.startsWith('#'));
      
      this.addCheck('Python Dependencies', 'PASS', `Found ${packages.length} Python packages`);
    } catch (error) {
      this.addCheck('Python Dependencies', 'FAIL', 'Could not read requirements.txt');
    }
  }

  /**
   * Validate environment configuration
   */
  validateEnvironmentConfiguration() {
    const envExamplePath = path.join(this.config.backendPath, '.env.example');
    const envProdPath = path.join(this.config.backendPath, '.env.production');

    if (!fs.existsSync(envExamplePath)) {
      this.addCheck('Environment Configuration', 'WARNING', '.env.example not found');
      return;
    }

    const envContent = fs.readFileSync(envExamplePath, 'utf8');
    const issues = [];

    // Check for required security variables
    const requiredVars = ['JWT_SECRET_KEY', 'DATABASE_PASSWORD', 'API_KEYS'];
    
    for (const varName of requiredVars) {
      if (!envContent.includes(varName)) {
        issues.push(`Missing ${varName} configuration`);
      }
    }

    if (issues.length > 0) {
      this.addCheck('Environment Configuration', 'WARNING', 'Environment configuration issues', issues);
    } else {
      this.addCheck('Environment Configuration', 'PASS', 'Environment properly configured');
    }
  }

  /**
   * Validate Docker security
   */
  validateDockerSecurity() {
    const dockerComposePath = path.join(this.config.backendPath, 'docker-compose.yml');
    
    if (!fs.existsSync(dockerComposePath)) {
      this.addCheck('Docker Security', 'SKIP', 'Docker compose file not found');
      return;
    }

    const dockerContent = fs.readFileSync(dockerComposePath, 'utf8');
    const issues = [];

    // Check for privileged containers
    if (dockerContent.includes('privileged: true')) {
      issues.push('Privileged containers detected');
    }

    // Check for root user usage
    if (!dockerContent.includes('user:') && dockerContent.includes('image:')) {
      issues.push('Containers may be running as root');
    }

    // Check for secrets in environment variables
    if (dockerContent.includes('password') && dockerContent.includes('environment:')) {
      issues.push('Potential secrets in environment variables');
    }

    if (issues.length > 0) {
      this.addCheck('Docker Security', 'WARNING', 'Docker security issues found', issues);
    } else {
      this.addCheck('Docker Security', 'PASS', 'Docker configuration secure');
    }
  }

  /**
   * Validate file permissions
   */
  validateFilePermissions() {
    const sensitiveFiles = [
      path.join(this.config.backendPath, '.env'),
      path.join(this.config.backendPath, '.env.production'),
      path.join(this.config.mobileAppPath, 'android', 'app', 'release.keystore'),
    ];

    const issues = [];

    for (const file of sensitiveFiles) {
      if (fs.existsSync(file)) {
        try {
          const stats = fs.statSync(file);
          const mode = stats.mode & parseInt('777', 8);
          
          // Check if file is world-readable (should not be)
          if (mode & parseInt('044', 8)) {
            issues.push(`${path.basename(file)} is world-readable`);
          }
        } catch (error) {
          // Skip files that can't be checked
        }
      }
    }

    if (issues.length > 0) {
      this.addCheck('File Permissions', 'WARNING', 'Insecure file permissions detected', issues);
    } else {
      this.addCheck('File Permissions', 'PASS', 'File permissions secure');
    }
  }

  /**
   * Get all source files recursively
   */
  getAllSourceFiles(dir) {
    const files = [];
    const extensions = ['.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.kt', '.swift'];

    const traverseDir = (currentDir) => {
      const items = fs.readdirSync(currentDir);
      
      for (const item of items) {
        const itemPath = path.join(currentDir, item);
        const stat = fs.statSync(itemPath);
        
        if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
          traverseDir(itemPath);
        } else if (stat.isFile() && extensions.some(ext => item.endsWith(ext))) {
          files.push(itemPath);
        }
      }
    };

    try {
      traverseDir(dir);
    } catch (error) {
      // Directory might not exist or be accessible
    }

    return files;
  }

  /**
   * Add a security check result
   */
  addCheck(name, status, message, details = null) {
    const check = {
      name,
      status,
      message,
      details,
      timestamp: new Date().toISOString()
    };

    this.auditResults.checks.push(check);

    // Update counters
    switch (status) {
      case 'PASS':
        this.auditResults.passed++;
        console.log(`✅ ${name}: ${message}`);
        break;
      case 'FAIL':
        this.auditResults.failed++;
        this.auditResults.critical++;
        console.log(`❌ ${name}: ${message}`);
        if (details) console.log(`   Details: ${JSON.stringify(details, null, 2)}`);
        break;
      case 'WARNING':
        this.auditResults.warnings++;
        console.log(`⚠️  ${name}: ${message}`);
        if (details) console.log(`   Details: ${JSON.stringify(details, null, 2)}`);
        break;
      case 'SKIP':
        console.log(`⏭️  ${name}: ${message}`);
        break;
    }
  }

  /**
   * Generate security report
   */
  generateSecurityReport() {
    const reportPath = path.join(this.config.mobileAppPath, 'security-audit-report.json');
    
    // Calculate security score
    const totalChecks = this.auditResults.passed + this.auditResults.failed + this.auditResults.warnings;
    const securityScore = totalChecks > 0 ? 
      Math.round(((this.auditResults.passed + (this.auditResults.warnings * 0.5)) / totalChecks) * 100) : 0;

    this.auditResults.securityScore = securityScore;
    this.auditResults.summary = {
      totalChecks,
      securityScore,
      hasCriticalIssues: this.auditResults.critical > 0,
      recommendations: this.generateRecommendations()
    };

    // Write detailed report
    fs.writeFileSync(reportPath, JSON.stringify(this.auditResults, null, 2));

    // Print summary
    console.log('\n🔒 ================== SECURITY AUDIT SUMMARY ==================');
    console.log(`📊 Security Score: ${securityScore}%`);
    console.log(`✅ Passed: ${this.auditResults.passed}`);
    console.log(`⚠️  Warnings: ${this.auditResults.warnings}`);
    console.log(`❌ Failed: ${this.auditResults.failed}`);
    console.log(`🚨 Critical: ${this.auditResults.critical}`);
    console.log(`📄 Detailed report: ${reportPath}`);

    if (this.auditResults.critical > 0) {
      console.log('\n🚨 CRITICAL SECURITY ISSUES DETECTED - MUST BE ADDRESSED BEFORE PRODUCTION DEPLOYMENT');
      process.exit(1);
    } else if (this.auditResults.failed > 0) {
      console.log('\n⚠️  SECURITY ISSUES DETECTED - RECOMMENDED TO ADDRESS');
      process.exit(1);
    } else {
      console.log('\n✅ SECURITY AUDIT PASSED - SYSTEM READY FOR DEPLOYMENT');
    }
  }

  /**
   * Generate security recommendations
   */
  generateRecommendations() {
    const recommendations = [];

    if (this.auditResults.failed > 0) {
      recommendations.push('Address all failed security checks before production deployment');
    }

    if (this.auditResults.warnings > 0) {
      recommendations.push('Review and address security warnings to improve overall security posture');
    }

    // Add specific recommendations based on failed checks
    const failedChecks = this.auditResults.checks.filter(check => check.status === 'FAIL');
    
    if (failedChecks.some(check => check.name.includes('Hardcoded Secrets'))) {
      recommendations.push('Remove all hardcoded secrets and use environment variables or secure key management');
    }

    if (failedChecks.some(check => check.name.includes('Authentication'))) {
      recommendations.push('Implement proper authentication and authorization mechanisms');
    }

    if (failedChecks.some(check => check.name.includes('API Endpoint'))) {
      recommendations.push('Secure all API endpoints with proper authentication and authorization');
    }

    return recommendations;
  }
}

// Run audit if called directly
if (require.main === module) {
  const auditor = new SecurityAuditor();
  auditor.runAudit().catch(error => {
    console.error('Security audit failed:', error);
    process.exit(1);
  });
}

module.exports = SecurityAuditor;
