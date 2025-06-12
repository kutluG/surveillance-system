/**
 * HLS Parser Utility for extracting quality levels from HLS master playlists
 * Supports client-side parsing of m3u8 files for adaptive bitrate streaming
 */

import * as HLS from 'hls-parser';

interface HLSQualityLevel {
  bandwidth: number;
  resolution: string;
  url: string;
  label: string;
}

interface HLSStreamInfo {
  bandwidth: number;
  resolution?: string;
  codecs?: string;
  url: string;
}

export class HLSParser {
  private baseUrl: string = '';

  /**
   * Parse HLS master playlist to extract quality levels
   * @param masterPlaylistUrl - URL to the master playlist
   * @returns Promise<HLSQualityLevel[]> - Array of quality levels
   */  async parsePlaylist(masterPlaylistUrl: string): Promise<HLSQualityLevel[]> {
    try {
      // Extract base URL for relative path resolution
      this.baseUrl = this.extractBaseUrl(masterPlaylistUrl);
      
      // Fetch the master playlist
      const response = await fetch(masterPlaylistUrl, {
        headers: {
          'User-Agent': 'SurveillanceApp/1.0.0',
          'Accept': 'application/vnd.apple.mpegurl, application/x-mpegurl, */*',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch playlist: ${response.status} ${response.statusText}`);
      }

      const playlistContent = await response.text();
      
      // Use hls-parser library to parse the content
      const parsedPlaylist = HLS.parse(playlistContent);
      
      if (!parsedPlaylist.isMasterPlaylist) {
        throw new Error('Provided URL does not point to a master playlist');
      }

      return this.extractQualityLevelsFromParsed(parsedPlaylist);
    } catch (error) {
      console.error('HLS Parser error:', error);
      // Fallback to custom parsing for compatibility
      try {
        const response = await fetch(masterPlaylistUrl, {
          headers: {
            'User-Agent': 'SurveillanceApp/1.0.0',
            'Accept': 'application/vnd.apple.mpegurl, application/x-mpegurl, */*',
          },
        });
        const playlistContent = await response.text();
        return this.parseM3U8Content(playlistContent);
      } catch (fallbackError) {
        throw new Error(`Failed to parse HLS playlist: ${error.message}`);
      }
    }
  }

  /**
   * Extract quality levels from parsed HLS playlist
   * @param parsedPlaylist - Parsed HLS master playlist
   * @returns HLSQualityLevel[] - Array of quality levels
   */
  private extractQualityLevelsFromParsed(parsedPlaylist: any): HLSQualityLevel[] {
    const variants = parsedPlaylist.variants || [];
    
    // Sort variants by bandwidth (ascending)
    variants.sort((a: any, b: any) => a.bandwidth - b.bandwidth);

    return variants.map((variant: any, index: number) => {
      const resolution = variant.resolution ? `${variant.resolution.width}x${variant.resolution.height}` : 'Unknown';
      const url = this.resolveUrl(variant.uri);
      const label = this.generateQualityLabel(variant.bandwidth, resolution, index, variants.length);

      return {
        bandwidth: variant.bandwidth,
        resolution,
        url,
        label,
      };
    });
  }

  /**
   * Parse M3U8 content and extract stream information
   * @param content - Raw M3U8 playlist content
   * @returns HLSQualityLevel[] - Parsed quality levels
   */
  private parseM3U8Content(content: string): HLSQualityLevel[] {
    const lines = content.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    const streams: HLSStreamInfo[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Look for EXT-X-STREAM-INF tags
      if (line.startsWith('#EXT-X-STREAM-INF:')) {
        const streamInfo = this.parseStreamInfo(line);
        const nextLine = lines[i + 1];
        
        // Next line should be the stream URL
        if (nextLine && !nextLine.startsWith('#')) {
          streamInfo.url = this.resolveUrl(nextLine);
          streams.push(streamInfo);
        }
      }
    }

    // Sort streams by bandwidth (ascending)
    streams.sort((a, b) => a.bandwidth - b.bandwidth);

    // Convert to quality levels with meaningful labels
    return streams.map((stream, index) => this.createQualityLevel(stream, index, streams.length));
  }

  /**
   * Parse EXT-X-STREAM-INF line to extract stream attributes
   * @param line - EXT-X-STREAM-INF line
   * @returns HLSStreamInfo - Parsed stream information
   */
  private parseStreamInfo(line: string): HLSStreamInfo {
    const attributes = this.parseAttributes(line);
    
    return {
      bandwidth: parseInt(attributes.BANDWIDTH) || 0,
      resolution: attributes.RESOLUTION,
      codecs: attributes.CODECS,
      url: '',
    };
  }

  /**
   * Parse attributes from M3U8 tag line
   * @param line - Tag line with attributes
   * @returns Record<string, string> - Parsed attributes
   */
  private parseAttributes(line: string): Record<string, string> {
    const attributes: Record<string, string> = {};
    const attributeRegex = /([A-Z-]+)=("[^"]*"|[^,]*)/g;
    let match;

    while ((match = attributeRegex.exec(line)) !== null) {
      const key = match[1];
      let value = match[2];
      
      // Remove quotes if present
      if (value.startsWith('"') && value.endsWith('"')) {
        value = value.slice(1, -1);
      }
      
      attributes[key] = value;
    }

    return attributes;
  }

  /**
   * Create quality level object with meaningful labels
   * @param stream - Stream information
   * @param index - Stream index
   * @param totalStreams - Total number of streams
   * @returns HLSQualityLevel - Quality level object
   */
  private createQualityLevel(stream: HLSStreamInfo, index: number, totalStreams: number): HLSQualityLevel {
    // Extract resolution dimensions if available
    let resolution = stream.resolution || 'Unknown';
    let label = this.generateQualityLabel(stream.bandwidth, stream.resolution, index, totalStreams);

    return {
      bandwidth: stream.bandwidth,
      resolution,
      url: stream.url,
      label,
    };
  }

  /**
   * Generate meaningful quality labels based on bandwidth and resolution
   * @param bandwidth - Stream bandwidth
   * @param resolution - Stream resolution
   * @param index - Stream index
   * @param totalStreams - Total number of streams
   * @returns string - Quality label
   */
  private generateQualityLabel(
    bandwidth: number, 
    resolution?: string, 
    index: number = 0, 
    totalStreams: number = 1
  ): string {
    // Try to extract height from resolution (e.g., "1920x1080" -> 1080)
    if (resolution) {
      const heightMatch = resolution.match(/(\d+)x(\d+)/);
      if (heightMatch) {
        const height = parseInt(heightMatch[2]);
        
        // Common resolution mappings
        if (height >= 2160) return '4K';
        if (height >= 1440) return '1440p';
        if (height >= 1080) return '1080p';
        if (height >= 720) return '720p';
        if (height >= 480) return '480p';
        if (height >= 360) return '360p';
        if (height >= 240) return '240p';
        
        return `${height}p`;
      }
    }

    // Fallback to bandwidth-based labels
    const kbps = Math.round(bandwidth / 1000);
    
    if (kbps >= 5000) return 'Ultra High';
    if (kbps >= 2500) return 'High';
    if (kbps >= 1000) return 'Medium';
    if (kbps >= 500) return 'Low';
    
    // Last resort: use relative quality names
    if (totalStreams > 1) {
      if (index === totalStreams - 1) return 'Highest';
      if (index === 0) return 'Lowest';
      if (totalStreams === 3 && index === 1) return 'Medium';
    }
    
    return `${kbps}k`;
  }

  /**
   * Resolve relative URLs to absolute URLs
   * @param url - URL to resolve
   * @returns string - Resolved absolute URL
   */
  private resolveUrl(url: string): string {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    
    if (url.startsWith('/')) {
      // Absolute path - use protocol and host from base URL
      const baseUrlParts = new URL(this.baseUrl);
      return `${baseUrlParts.protocol}//${baseUrlParts.host}${url}`;
    }
    
    // Relative path - append to base URL directory
    return new URL(url, this.baseUrl).toString();
  }

  /**
   * Extract base URL from master playlist URL
   * @param url - Master playlist URL
   * @returns string - Base URL for resolving relative paths
   */
  private extractBaseUrl(url: string): string {
    try {
      const urlObj = new URL(url);
      // Remove filename from path to get directory
      const pathParts = urlObj.pathname.split('/');
      pathParts.pop(); // Remove filename
      urlObj.pathname = pathParts.join('/') + '/';
      return urlObj.toString();
    } catch (error) {
      console.warn('Failed to extract base URL:', error);
      return url;
    }
  }

  /**
   * Validate HLS playlist URL format
   * @param url - URL to validate
   * @returns boolean - True if URL appears to be valid HLS
   */
  static isValidHLSUrl(url: string): boolean {
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname.toLowerCase();
      return pathname.endsWith('.m3u8') || pathname.includes('playlist');
    } catch (error) {
      return false;
    }
  }

  /**
   * Get recommended quality based on network conditions
   * @param availableQualities - Available quality levels
   * @param networkType - Network type ('wifi', '4g', '3g', 'slow-2g')
   * @returns HLSQualityLevel | null - Recommended quality or null
   */
  static getRecommendedQuality(
    availableQualities: HLSQualityLevel[], 
    networkType?: string
  ): HLSQualityLevel | null {
    if (availableQualities.length === 0) return null;

    // Sort by bandwidth ascending
    const sortedQualities = [...availableQualities].sort((a, b) => a.bandwidth - b.bandwidth);

    switch (networkType) {
      case 'wifi':
        // Use highest quality for WiFi
        return sortedQualities[sortedQualities.length - 1];
      
      case '4g':
        // Use high-medium quality for 4G
        const highQualityIndex = Math.max(0, sortedQualities.length - 2);
        return sortedQualities[highQualityIndex];
      
      case '3g':
        // Use medium quality for 3G
        const mediumQualityIndex = Math.floor(sortedQualities.length / 2);
        return sortedQualities[mediumQualityIndex];
      
      case 'slow-2g':
      case '2g':
        // Use lowest quality for slow connections
        return sortedQualities[0];
      
      default:
        // Default to medium-high quality
        const defaultIndex = Math.max(0, sortedQualities.length - 2);
        return sortedQualities[defaultIndex];
    }
  }
}

export default HLSParser;
