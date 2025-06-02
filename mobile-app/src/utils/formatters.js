// Formatting utility functions
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined || isNaN(num)) return '0';
  
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};

export const formatPercentage = (value, total) => {
  if (total === 0) return '0%';
  const percentage = (value / total) * 100;
  return `${percentage.toFixed(1)}%`;
};

export const formatCurrency = (amount, currency = 'USD') => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount);
};

export const formatCameraName = (name) => {
  if (!name) return 'Unknown Camera';
  
  // Remove common prefixes and format
  return name
    .replace(/^(camera|cam)[\s\-_]*/i, '')
    .replace(/[\s\-_]+/g, ' ')
    .trim()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const formatAlertType = (type) => {
  if (!type) return 'Unknown';
  
  return type
    .replace(/[\s\-_]+/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const formatStatus = (status) => {
  const statusMap = {
    'online': 'Online',
    'offline': 'Offline',
    'recording': 'Recording',
    'idle': 'Idle',
    'error': 'Error',
    'maintenance': 'Maintenance',
    'active': 'Active',
    'inactive': 'Inactive',
    'acknowledged': 'Acknowledged',
    'dismissed': 'Dismissed'
  };
  
  return statusMap[status?.toLowerCase()] || status;
};

export const formatBandwidth = (bps) => {
  if (bps === 0) return '0 bps';
  
  const units = ['bps', 'Kbps', 'Mbps', 'Gbps'];
  const k = 1000;
  const i = Math.floor(Math.log(bps) / Math.log(k));
  
  return parseFloat((bps / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
};

export const formatLatency = (ms) => {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  } else {
    return `${(ms / 1000).toFixed(1)}s`;
  }
};

export const truncateText = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
};

export const formatLocation = (location) => {
  if (!location) return 'Unknown Location';
  
  return location
    .replace(/[\s\-_]+/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const formatResolution = (width, height) => {
  if (!width || !height) return 'Unknown';
  
  const commonResolutions = {
    '1920x1080': '1080p (Full HD)',
    '1280x720': '720p (HD)',
    '3840x2160': '4K (Ultra HD)',
    '2560x1440': '1440p (QHD)',
    '640x480': '480p (SD)'
  };
  
  const resolution = `${width}x${height}`;
  return commonResolutions[resolution] || resolution;
};

export const formatFrameRate = (fps) => {
  if (!fps) return 'Unknown';
  return `${fps} FPS`;
};

export const capitalizeFirst = (str) => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

export const formatPhoneNumber = (phone) => {
  if (!phone) return '';
  
  // Remove all non-digits
  const cleaned = phone.replace(/\D/g, '');
  
  // Format as (XXX) XXX-XXXX for US numbers
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  
  return phone; // Return original if not standard format
};
