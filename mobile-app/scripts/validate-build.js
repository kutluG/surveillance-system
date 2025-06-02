#!/usr/bin/env node

/**
 * Pre-build validation script
 * Runs before production builds to ensure configuration is correct
 */

const fs = require('fs');
const path = require('path');

class BuildValidator {
  constructor() {
    this.errors = [];
    this.warnings = [];
  }

  log(message) {
    console.log(`[BUILD VALIDATOR] ${message}`);
  }

  error(message) {
    this.errors.push(message);
    console.error(`❌ [ERROR] ${message}`);
  }

  warn(message) {
    this.warnings.push(message);
    console.warn(`⚠️  [WARNING] ${message}`);
  }

  async validate() {
    this.log('Starting build validation...');

    await this.validateEnvironmentFiles();
    await this.validatePackageJson();
    await this.validateConstants();
    await this.validateAssets();
    await this.validateSecurity();

    return this.showResults();
  }

  async validateEnvironmentFiles() {
    this.log('Validating environment files...');

    const envFiles = ['.env.development', '.env.production'];
    
    for (const envFile of envFiles) {
      const filePath = path.join(__dirname, '..', envFile);
      
      if (!fs.existsSync(filePath)) {
        this.error(`Missing environment file: ${envFile}`);
        continue;
      }

      const content = fs.readFileSync(filePath, 'utf8');
      const lines = content.split('\n').filter(line => line.trim() && !line.startsWith('#'));
      
      const requiredVars = [
        'API_BASE_URL',
        'WEBSOCKET_URL',
        'ENV',
        'PORT_AUTH',
        'PORT_CAMERA',
        'PORT_ALERTS',
        'PORT_DASHBOARD'
      ];

      for (const varName of requiredVars) {
        if (!lines.some(line => line.startsWith(`${varName}=`))) {
          this.error(`Missing required variable ${varName} in ${envFile}`);
        }
      }

      // Production-specific validations
      if (envFile === '.env.production') {
        const apiBaseUrl = lines.find(line => line.startsWith('API_BASE_URL='))?.split('=')[1];
        if (apiBaseUrl && apiBaseUrl.includes('localhost')) {
          this.error('Production environment should not use localhost URLs');
        }

        const debugMode = lines.find(line => line.startsWith('DEBUG='))?.split('=')[1];
        if (debugMode === 'true') {
          this.warn('Debug mode is enabled in production environment');
        }
      }
    }
  }

  async validatePackageJson() {
    this.log('Validating package.json...');

    const packagePath = path.join(__dirname, '..', 'package.json');
    
    if (!fs.existsSync(packagePath)) {
      this.error('Missing package.json file');
      return;
    }

    try {
      const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

      // Check required dependencies
      const requiredDeps = [
        'react',
        'react-native',
        'react-native-config',
        'axios',
        '@react-native-async-storage/async-storage'
      ];

      for (const dep of requiredDeps) {
        if (!packageJson.dependencies?.[dep]) {
          this.error(`Missing required dependency: ${dep}`);
        }
      }

      // Check version format
      if (!packageJson.version || !/^\d+\.\d+\.\d+/.test(packageJson.version)) {
        this.warn('Invalid version format in package.json');
      }

      // Check scripts
      const requiredScripts = ['android', 'ios', 'test', 'lint'];
      for (const script of requiredScripts) {
        if (!packageJson.scripts?.[script]) {
          this.warn(`Missing script: ${script}`);
        }
      }

    } catch (error) {
      this.error(`Invalid package.json format: ${error.message}`);
    }
  }

  async validateConstants() {
    this.log('Validating constants file...');

    const constantsPath = path.join(__dirname, '..', 'src', 'constants', 'index.js');
    
    if (!fs.existsSync(constantsPath)) {
      this.error('Missing constants file: src/constants/index.js');
      return;
    }

    const content = fs.readFileSync(constantsPath, 'utf8');

    // Check for required exports
    const requiredExports = ['API_CONFIG', 'COLORS', 'SIZES'];
    for (const exportName of requiredExports) {
      if (!content.includes(`export const ${exportName}`)) {
        this.error(`Missing required export: ${exportName}`);
      }
    }

    // Check for hardcoded localhost URLs
    if (content.includes('localhost') && process.env.NODE_ENV === 'production') {
      this.warn('Constants file contains localhost URLs');
    }
  }

  async validateAssets() {
    this.log('Validating assets...');

    const androidIconPath = path.join(__dirname, '..', 'android', 'app', 'src', 'main', 'res');
    const iosIconPath = path.join(__dirname, '..', 'ios', 'SurveillanceApp', 'Images.xcassets');

    // Check Android icons
    if (!fs.existsSync(androidIconPath)) {
      this.warn('Android icon resources directory not found');
    } else {
      const iconDirs = ['mipmap-hdpi', 'mipmap-mdpi', 'mipmap-xhdpi', 'mipmap-xxhdpi', 'mipmap-xxxhdpi'];
      for (const dir of iconDirs) {
        const dirPath = path.join(androidIconPath, dir);
        if (fs.existsSync(dirPath)) {
          const icLauncherPath = path.join(dirPath, 'ic_launcher.png');
          if (!fs.existsSync(icLauncherPath)) {
            this.warn(`Missing ic_launcher.png in ${dir}`);
          }
        }
      }
    }

    // Check iOS icons
    if (!fs.existsSync(iosIconPath)) {
      this.warn('iOS assets directory not found');
    }
  }

  async validateSecurity() {
    this.log('Validating security configuration...');

    // Check for sensitive data in source code
    const sensitivePatterns = [
      /password\s*=\s*["']/i,
      /api_key\s*=\s*["']/i,
      /secret\s*=\s*["']/i,
      /token\s*=\s*["'][^"']*["']/i
    ];

    const sourceDir = path.join(__dirname, '..', 'src');
    const files = this.getAllJSFiles(sourceDir);

    for (const file of files) {
      const content = fs.readFileSync(file, 'utf8');
      
      for (const pattern of sensitivePatterns) {
        if (pattern.test(content)) {
          this.warn(`Potential sensitive data found in ${path.relative(sourceDir, file)}`);
        }
      }
    }

    // Check network security config (Android)
    const networkConfigPath = path.join(__dirname, '..', 'android', 'app', 'src', 'main', 'res', 'xml', 'network_security_config.xml');
    if (!fs.existsSync(networkConfigPath)) {
      this.warn('Missing network security configuration for Android');
    }
  }

  getAllJSFiles(dir) {
    const files = [];
    
    if (!fs.existsSync(dir)) return files;

    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      
      if (entry.isDirectory() && !entry.name.startsWith('.')) {
        files.push(...this.getAllJSFiles(fullPath));
      } else if (entry.isFile() && /\.(js|jsx|ts|tsx)$/.test(entry.name)) {
        files.push(fullPath);
      }
    }
    
    return files;
  }

  showResults() {
    console.log('\n' + '='.repeat(50));
    console.log('BUILD VALIDATION RESULTS');
    console.log('='.repeat(50));

    if (this.errors.length === 0 && this.warnings.length === 0) {
      console.log('✅ All validations passed!');
      return true;
    }

    if (this.errors.length > 0) {
      console.log('\n❌ ERRORS:');
      this.errors.forEach((error, index) => {
        console.log(`  ${index + 1}. ${error}`);
      });
    }

    if (this.warnings.length > 0) {
      console.log('\n⚠️  WARNINGS:');
      this.warnings.forEach((warning, index) => {
        console.log(`  ${index + 1}. ${warning}`);
      });
    }

    console.log('\n' + '='.repeat(50));

    if (this.errors.length > 0) {
      console.log('❌ Build validation failed. Please fix the errors above.');
      return false;
    } else {
      console.log('⚠️  Build validation passed with warnings.');
      return true;
    }
  }
}

// Run validation if called directly
if (require.main === module) {
  const validator = new BuildValidator();
  validator.validate().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('Build validation crashed:', error);
    process.exit(1);
  });
}

module.exports = BuildValidator;
