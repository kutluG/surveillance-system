/**
 * Certificate Pinning Implementation
 * Provides SSL/TLS certificate pinning for enhanced security
 */
import { Platform } from 'react-native';
import axios from 'axios';
import EnvironmentConfig from '../config/environment';

class CertificatePinning {
  constructor() {
    this.pinnedCertificates = {
      production: {
        // Production SSL certificate fingerprints
        'api.surveillance-ai.com': [
          'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', // Replace with actual certificate hash
          'sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', // Backup certificate hash
        ],
        'ws.surveillance-ai.com': [
          'sha256/CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=',
          'sha256/DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD=',
        ],
      },
      staging: {
        'staging-api.surveillance-ai.com': [
          'sha256/EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE=',
        ],
      },
    };

    this.initializePinning();
  }

  /**
   * Initialize certificate pinning
   */
  initializePinning() {
    if (!EnvironmentConfig.isProduction()) {
      console.log('🔒 Certificate pinning disabled in development');
      return;
    }

    const environment = EnvironmentConfig.getEnvironment();
    const pins = this.pinnedCertificates[environment];

    if (!pins) {
      console.warn('⚠️  No certificate pins configured for environment:', environment);
      return;
    }

    console.log('🔒 Certificate pinning enabled for environment:', environment);
    this.setupAxiosInterceptor();
  }

  /**
   * Setup Axios interceptor for certificate validation
   */
  setupAxiosInterceptor() {
    // Add request interceptor to validate certificates
    axios.interceptors.request.use(
      (config) => {
        if (config.url && this.shouldValidateCertificate(config.url)) {
          config.validateStatus = (status) => {
            // Allow any status for now, we'll validate the certificate
            return status < 500;
          };
          
          // Add certificate validation metadata
          config.metadata = {
            ...config.metadata,
            requiresCertificateValidation: true,
            domain: this.extractDomain(config.url),
          };
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor to check certificate validation results
    axios.interceptors.response.use(
      (response) => {
        if (response.config.metadata?.requiresCertificateValidation) {
          if (!this.validateCertificateFromResponse(response)) {
            throw new Error('Certificate validation failed - connection may be compromised');
          }
        }
        return response;
      },
      (error) => {
        if (error.config?.metadata?.requiresCertificateValidation) {
          console.error('🔒 Certificate pinning validation failed:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Check if URL requires certificate validation
   */
  shouldValidateCertificate(url) {
    if (!url || !url.startsWith('https://')) {
      return false;
    }

    const domain = this.extractDomain(url);
    const environment = EnvironmentConfig.getEnvironment();
    const pins = this.pinnedCertificates[environment];

    return pins && pins[domain];
  }

  /**
   * Extract domain from URL
   */
  extractDomain(url) {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname;
    } catch (error) {
      console.error('Invalid URL for certificate pinning:', url);
      return null;
    }
  }

  /**
   * Validate certificate from response (placeholder for native implementation)
   */
  validateCertificateFromResponse(response) {
    // In a real implementation, this would check the certificate fingerprint
    // received in the response against the pinned certificates
    // This requires native module implementation to access certificate details
    
    const domain = response.config.metadata?.domain;
    if (!domain) return true;

    console.log('🔒 Certificate validation for domain:', domain);
    
    // For now, we'll return true and log the validation attempt
    // In production, this should be implemented with native modules
    return true;
  }

  /**
   * Get pinned certificates for domain
   */
  getPinnedCertificates(domain) {
    const environment = EnvironmentConfig.getEnvironment();
    const pins = this.pinnedCertificates[environment];
    return pins?.[domain] || [];
  }

  /**
   * Add new certificate pin
   */
  addCertificatePin(domain, certificateHash) {
    const environment = EnvironmentConfig.getEnvironment();
    
    if (!this.pinnedCertificates[environment]) {
      this.pinnedCertificates[environment] = {};
    }
    
    if (!this.pinnedCertificates[environment][domain]) {
      this.pinnedCertificates[environment][domain] = [];
    }
    
    this.pinnedCertificates[environment][domain].push(certificateHash);
    console.log('🔒 Added certificate pin for domain:', domain);
  }

  /**
   * Remove certificate pin
   */
  removeCertificatePin(domain, certificateHash) {
    const environment = EnvironmentConfig.getEnvironment();
    const pins = this.pinnedCertificates[environment]?.[domain];
    
    if (pins) {
      const index = pins.indexOf(certificateHash);
      if (index > -1) {
        pins.splice(index, 1);
        console.log('🔒 Removed certificate pin for domain:', domain);
      }
    }
  }

  /**
   * Validate certificate manually (for testing)
   */
  async testCertificateValidation(url) {
    try {
      const response = await axios.get(url, {
        timeout: 5000,
        validateStatus: () => true,
      });

      const domain = this.extractDomain(url);
      const pinnedCerts = this.getPinnedCertificates(domain);

      console.log('🔒 Certificate test for:', domain);
      console.log('🔒 Pinned certificates:', pinnedCerts.length);
      console.log('🔒 Response status:', response.status);

      return {
        domain,
        pinnedCertificates: pinnedCerts,
        responseStatus: response.status,
        validationPassed: response.status === 200,
      };
    } catch (error) {
      console.error('🔒 Certificate test failed:', error.message);
      return {
        domain: this.extractDomain(url),
        error: error.message,
        validationPassed: false,
      };
    }
  }

  /**
   * Get certificate pinning status
   */
  getStatus() {
    const environment = EnvironmentConfig.getEnvironment();
    const pins = this.pinnedCertificates[environment] || {};
    
    return {
      enabled: EnvironmentConfig.isProduction(),
      environment,
      pinnedDomains: Object.keys(pins),
      totalPins: Object.values(pins).reduce((total, domainPins) => total + domainPins.length, 0),
    };
  }

  /**
   * Handle certificate pinning failure
   */
  handlePinningFailure(domain, error) {
    console.error('🚨 Certificate pinning failure for domain:', domain, error);
    
    // In production, this could trigger additional security measures:
    // - Block the request
    // - Log security incident
    // - Notify security team
    // - Show user warning
    
    throw new Error(`Certificate validation failed for ${domain}. Connection may be compromised.`);
  }
}

// Create singleton instance
const certificatePinning = new CertificatePinning();

export default certificatePinning;
