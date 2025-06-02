import React, { memo, useCallback, useMemo } from 'react';
import { View, FlatList, VirtualizedList } from 'react-native';
import performanceService from '../services/performanceService';

// Higher-order component for performance monitoring
export const withPerformanceMonitoring = (WrappedComponent, componentName) => {
  return memo((props) => {
    const startTime = useMemo(() => Date.now(), []);
    
    React.useEffect(() => {
      const endTime = Date.now();
      performanceService.measureRenderTime(componentName, startTime, endTime);
    }, [startTime]);
    
    return <WrappedComponent {...props} />;
  });
};

// Optimized FlatList component
export const OptimizedFlatList = memo(({
  data,
  renderItem,
  keyExtractor,
  itemHeight,
  ...props
}) => {
  const getItemLayout = useCallback((data, index) => ({
    length: itemHeight,
    offset: itemHeight * index,
    index,
  }), [itemHeight]);

  const memoizedRenderItem = useCallback(renderItem, [renderItem]);
  const memoizedKeyExtractor = useCallback(keyExtractor, [keyExtractor]);

  return (
    <FlatList
      data={data}
      renderItem={memoizedRenderItem}
      keyExtractor={memoizedKeyExtractor}
      getItemLayout={itemHeight ? getItemLayout : undefined}
      removeClippedSubviews={true}
      maxToRenderPerBatch={10}
      updateCellsBatchingPeriod={50}
      initialNumToRender={10}
      windowSize={10}
      legacyImplementation={false}
      {...props}
    />
  );
});

// Lazy loading wrapper
export const LazyComponent = ({ children, placeholder = null, threshold = 100 }) => {
  const [isVisible, setIsVisible] = React.useState(false);
  const ref = React.useRef();

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: `${threshold}px` }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return (
    <View ref={ref}>
      {isVisible ? children : placeholder}
    </View>
  );
};

// Memoized selector hook
export const useMemoizedSelector = (selector, equalityFn = (a, b) => a === b) => {
  const selectedValue = useSelector(selector);
  const memoizedValue = useMemo(() => selectedValue, [selectedValue]);
  
  const previousValue = React.useRef(memoizedValue);
  
  if (!equalityFn(previousValue.current, memoizedValue)) {
    previousValue.current = memoizedValue;
  }
  
  return previousValue.current;
};

// Debounced callback hook
export const useDebouncedCallback = (callback, delay) => {
  const timeoutRef = React.useRef();
  
  return useCallback((...args) => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => callback(...args), delay);
  }, [callback, delay]);
};

// Throttled callback hook
export const useThrottledCallback = (callback, delay) => {
  const lastExecution = React.useRef(0);
  
  return useCallback((...args) => {
    const now = Date.now();
    if (now - lastExecution.current >= delay) {
      lastExecution.current = now;
      callback(...args);
    }
  }, [callback, delay]);
};

// Memory management hook
export const useMemoryOptimization = () => {
  const [memoryPressure, setMemoryPressure] = React.useState(false);
  
  React.useEffect(() => {
    const checkMemory = async () => {
      const memoryInfo = await performanceService.getMemoryInfo();
      const pressureThreshold = 80 * 1024 * 1024; // 80MB
      setMemoryPressure(memoryInfo.used > pressureThreshold);
    };
    
    const interval = setInterval(checkMemory, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const optimizeMemory = useCallback(async () => {
    await performanceService.handleHighMemoryUsage();
  }, []);
  
  return { memoryPressure, optimizeMemory };
};

// Component preloader
export const ComponentPreloader = ({ components = [] }) => {
  React.useEffect(() => {
    // Preload components in the background
    const preloadComponents = async () => {
      for (const component of components) {
        try {
          await component();
        } catch (error) {
          console.warn('Failed to preload component:', error);
        }
      }
    };
    
    // Use requestIdleCallback if available
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(preloadComponents);
    } else {
      setTimeout(preloadComponents, 1000);
    }
  }, [components]);
  
  return null;
};

// Image optimization component
export const OptimizedImage = memo(({ 
  source, 
  width, 
  height, 
  quality = 0.8,
  placeholder,
  ...props 
}) => {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  
  const optimizedSource = useMemo(() => {
    if (typeof source === 'string') {
      // Add optimization parameters to URL
      const url = new URL(source);
      url.searchParams.set('w', width.toString());
      url.searchParams.set('h', height.toString());
      url.searchParams.set('q', (quality * 100).toString());
      return { uri: url.toString() };
    }
    return source;
  }, [source, width, height, quality]);
  
  const onLoad = useCallback(() => {
    setLoading(false);
  }, []);
  
  const onError = useCallback(() => {
    setLoading(false);
    setError(true);
  }, []);
  
  if (error) {
    return placeholder || <View style={{ width, height, backgroundColor: '#f0f0f0' }} />;
  }
  
  return (
    <Image
      source={optimizedSource}
      style={{ width, height }}
      onLoad={onLoad}
      onError={onError}
      {...props}
    />
  );
});

export default {
  withPerformanceMonitoring,
  OptimizedFlatList,
  LazyComponent,
  useMemoizedSelector,
  useDebouncedCallback,
  useThrottledCallback,
  useMemoryOptimization,
  ComponentPreloader,
  OptimizedImage,
};
