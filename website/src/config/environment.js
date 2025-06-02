// Environment configuration helper
const config = {
  development: {
    API_BASE_URL: 'http://localhost:8001',
    WEBSOCKET_URL: 'ws://localhost:8002/ws',
    DEBUG: true,
    MOCK_DATA: true
  },
  production: {
    API_BASE_URL: 'https://api.surveillance-ai.com',
    WEBSOCKET_URL: 'wss://ws.surveillance-ai.com',
    DEBUG: false,
    MOCK_DATA: false
  }
};

const getConfig = () => {
  const env = process.env.REACT_APP_ENV || 'development';
  return {
    ...config[env],
    ENV: env,
    VERSION: process.env.REACT_APP_VERSION || '1.0.0'
  };
};

export default getConfig;
