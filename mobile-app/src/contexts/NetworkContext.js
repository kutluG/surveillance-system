import React, {createContext, useContext, useState, useEffect} from 'react';
import NetInfo from '@react-native-community/netinfo';
import {websocketService} from '../services/websocketService';

const NetworkContext = createContext({});

export const useNetwork = () => {
  const context = useContext(NetworkContext);
  if (!context) {
    throw new Error('useNetwork must be used within a NetworkProvider');
  }
  return context;
};

export const NetworkProvider = ({children}) => {
  const [isConnected, setIsConnected] = useState(true);
  const [connectionType, setConnectionType] = useState('unknown');
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsConnected(state.isConnected);
      setConnectionType(state.type);
      
      if (state.isConnected) {
        websocketService.connect();
      } else {
        websocketService.disconnect();
      }
    });

    // WebSocket connection status
    websocketService.onConnectionChange((connected) => {
      setWsConnected(connected);
    });

    return () => {
      unsubscribe();
      websocketService.disconnect();
    };
  }, []);

  const value = {
    isConnected,
    connectionType,
    wsConnected,
  };

  return (
    <NetworkContext.Provider value={value}>
      {children}
    </NetworkContext.Provider>
  );
};
