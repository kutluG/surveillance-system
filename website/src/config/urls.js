// URL configuration for different environments
import getConfig from './environment';

const config = getConfig();

export const getServiceUrls = () => {
  const isProduction = config.ENV === 'production';
  
  return {
    api: config.API_BASE_URL,
    websocket: config.WEBSOCKET_URL,
    grafana: isProduction ? 'https://monitoring.surveillance-ai.com' : 'http://localhost:3000',
    prometheus: isProduction ? 'https://metrics.surveillance-ai.com' : 'http://localhost:9090',
    apiGateway: isProduction ? 'https://gateway.surveillance-ai.com' : 'http://localhost:8000',
    docs: isProduction ? 'https://api.surveillance-ai.com/docs' : 'http://localhost:8001/docs'
  };
};

export const getDisplayUrls = () => {
  const urls = getServiceUrls();
  const isProduction = config.ENV === 'production';
  
  return {
    ...urls,
    // For documentation display - show both environments
    examples: {
      development: {
        grafana: 'http://localhost:3000',
        prometheus: 'http://localhost:9090',
        api: 'http://localhost:8001',
        websocket: 'ws://localhost:8002/ws'
      },
      production: {
        grafana: 'https://monitoring.surveillance-ai.com',
        prometheus: 'https://metrics.surveillance-ai.com', 
        api: 'https://api.surveillance-ai.com',
        websocket: 'wss://ws.surveillance-ai.com'
      }
    }
  };
};
