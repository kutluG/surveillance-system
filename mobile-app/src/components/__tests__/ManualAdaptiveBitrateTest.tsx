/**
 * Manual Test Suite for CameraView Adaptive Bitrate Streaming
 * 
 * This file contains manual test scenarios to verify the adaptive bitrate
 * functionality works correctly with real HLS streams.
 */

import React from 'react';
import { View, StyleSheet, ScrollView, Text, TouchableOpacity, Alert } from 'react-native';
import CameraView from '../components/CameraView';

// Test HLS URLs with multiple quality variants
const TEST_HLS_STREAMS = {
  // Apple's official test streams
  appleBasic: 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
  
  // Big Buck Bunny test streams with multiple variants
  bigBuckBunny: 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
  
  // Sintel test stream
  sintel: 'https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8',
  
  // Custom test stream (replace with your own)
  custom: 'https://example.com/your-test-stream/master.m3u8',
};

interface ManualTestProps {
  navigation?: any;
}

const ManualAdaptiveBitrateTest: React.FC<ManualTestProps> = ({ navigation }) => {
  const [currentStream, setCurrentStream] = React.useState<string>(TEST_HLS_STREAMS.appleBasic);
  const [testResults, setTestResults] = React.useState<Array<{ test: string; result: string; timestamp: string }>>([]);

  const logTestResult = (testName: string, result: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setTestResults(prev => [...prev, { test: testName, result, timestamp }]);
  };

  const runAutoQualityTest = () => {
    Alert.alert(
      'Auto Quality Test',
      'Follow these steps:\n\n' +
      '1. Ensure "Auto Quality" is ON (default)\n' +
      '2. Watch the video for 30 seconds\n' +
      '3. Switch between WiFi and mobile data\n' +
      '4. Check if quality changes automatically\n' +
      '5. Look for smooth transitions without buffering\n\n' +
      'Expected: Quality should adapt to network conditions automatically',
      [
        { text: 'Failed', onPress: () => logTestResult('Auto Quality Network Adaptation', 'FAILED') },
        { text: 'Passed', onPress: () => logTestResult('Auto Quality Network Adaptation', 'PASSED') },
      ]
    );
  };

  const runManualQualityTest = () => {
    Alert.alert(
      'Manual Quality Test',
      'Follow these steps:\n\n' +
      '1. Tap the quality button (HD icon)\n' +
      '2. Turn OFF "Auto Quality"\n' +
      '3. Select "360p" from the dropdown\n' +
      '4. Confirm video switches to 360p stream\n' +
      '5. Check that quality indicator shows "360P"\n' +
      '6. Try selecting other qualities (720p, 1080p)\n\n' +
      'Expected: Video should use exact quality selected',
      [
        { text: 'Failed', onPress: () => logTestResult('Manual Quality Selection', 'FAILED') },
        { text: 'Passed', onPress: () => logTestResult('Manual Quality Selection', 'PASSED') },
      ]
    );
  };

  const runBufferingTest = () => {
    Alert.alert(
      'Buffering & Smoothness Test',
      'Follow these steps:\n\n' +
      '1. Start with Auto Quality ON\n' +
      '2. Monitor for buffering events\n' +
      '3. Switch to slow network (2G simulation)\n' +
      '4. Watch how the player adapts\n' +
      '5. Check for minimal buffering/smooth playback\n\n' +
      'Expected: Minimal buffering, smooth quality transitions',
      [
        { text: 'Failed', onPress: () => logTestResult('Buffering & Smoothness', 'FAILED') },
        { text: 'Passed', onPress: () => logTestResult('Buffering & Smoothness', 'PASSED') },
      ]
    );
  };

  const runPersistenceTest = () => {
    Alert.alert(
      'Settings Persistence Test',
      'Follow these steps:\n\n' +
      '1. Turn OFF Auto Quality\n' +
      '2. Select a specific quality (e.g., 720p)\n' +
      '3. Close and reopen the app\n' +
      '4. Check if settings are preserved\n' +
      '5. Verify the same quality is selected\n\n' +
      'Expected: Settings should persist across app restarts',
      [
        { text: 'Failed', onPress: () => logTestResult('Settings Persistence', 'FAILED') },
        { text: 'Passed', onPress: () => logTestResult('Settings Persistence', 'PASSED') },
      ]
    );
  };

  const clearResults = () => {
    setTestResults([]);
  };

  const exportResults = () => {
    const resultsText = testResults.map(
      r => `${r.timestamp}: ${r.test} - ${r.result}`
    ).join('\n');
    
    Alert.alert(
      'Test Results',
      resultsText || 'No test results available',
      [{ text: 'OK' }]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Adaptive Bitrate Manual Tests</Text>
      
      {/* Stream Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Test Stream Selection</Text>
        {Object.entries(TEST_HLS_STREAMS).map(([key, url]) => (
          <TouchableOpacity
            key={key}
            style={[
              styles.streamButton,
              currentStream === url && styles.streamButtonActive
            ]}
            onPress={() => setCurrentStream(url)}
          >
            <Text style={[
              styles.streamButtonText,
              currentStream === url && styles.streamButtonTextActive
            ]}>
              {key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1')}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Video Player */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Video Player</Text>
        <View style={styles.videoContainer}>
          <CameraView
            hlsMasterPlaylistUrl={currentStream}
            style={styles.video}
            onError={(error) => {
              logTestResult('Video Loading', `FAILED: ${error.message}`);
            }}
            onLoad={() => {
              logTestResult('Video Loading', 'PASSED');
            }}
          />
        </View>
      </View>

      {/* Test Buttons */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Manual Test Cases</Text>
        
        <TouchableOpacity style={styles.testButton} onPress={runAutoQualityTest}>
          <Text style={styles.testButtonText}>Test 1: Auto Quality Adaptation</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.testButton} onPress={runManualQualityTest}>
          <Text style={styles.testButtonText}>Test 2: Manual Quality Selection</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.testButton} onPress={runBufferingTest}>
          <Text style={styles.testButtonText}>Test 3: Buffering & Smoothness</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.testButton} onPress={runPersistenceTest}>
          <Text style={styles.testButtonText}>Test 4: Settings Persistence</Text>
        </TouchableOpacity>
      </View>

      {/* Test Results */}
      <View style={styles.section}>
        <View style={styles.resultsHeader}>
          <Text style={styles.sectionTitle}>Test Results</Text>
          <View style={styles.resultsButtons}>
            <TouchableOpacity style={styles.clearButton} onPress={clearResults}>
              <Text style={styles.clearButtonText}>Clear</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.exportButton} onPress={exportResults}>
              <Text style={styles.exportButtonText}>Export</Text>
            </TouchableOpacity>
          </View>
        </View>
        
        {testResults.length === 0 ? (
          <Text style={styles.noResults}>No test results yet. Run some tests above.</Text>
        ) : (
          testResults.map((result, index) => (
            <View key={index} style={styles.resultItem}>
              <Text style={styles.resultTime}>{result.timestamp}</Text>
              <Text style={styles.resultTest}>{result.test}</Text>
              <Text style={[
                styles.resultStatus,
                result.result.includes('PASSED') ? styles.resultPassed : styles.resultFailed
              ]}>
                {result.result}
              </Text>
            </View>
          ))
        )}
      </View>

      {/* Instructions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Testing Instructions</Text>
        <Text style={styles.instructions}>
          1. Select a test stream from the options above{'\n'}
          2. Wait for the video to load completely{'\n'}
          3. Run each test case by tapping the test buttons{'\n'}
          4. Follow the instructions in each test dialog{'\n'}
          5. Mark the test as PASSED or FAILED based on observed behavior{'\n'}
          6. Check the results section for a summary{'\n\n'}
          
          <Text style={styles.bold}>Network Testing Tips:</Text>{'\n'}
          • Use device settings to simulate different network speeds{'\n'}
          • Switch between WiFi and mobile data{'\n'}
          • Monitor network usage in developer tools{'\n'}
          • Check for smooth quality transitions without freezing{'\n\n'}
          
          <Text style={styles.bold}>Quality Verification:</Text>{'\n'}
          • Open browser developer tools to monitor network requests{'\n'}
          • Check that different .m3u8 URLs are requested for different qualities{'\n'}
          • Verify visual quality changes match selected settings{'\n'}
          • Ensure bandwidth usage aligns with selected quality
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
    color: '#333',
  },
  section: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  streamButton: {
    backgroundColor: '#e0e0e0',
    padding: 12,
    borderRadius: 6,
    marginBottom: 8,
  },
  streamButtonActive: {
    backgroundColor: '#2196F3',
  },
  streamButtonText: {
    color: '#333',
    textAlign: 'center',
    fontWeight: '500',
  },
  streamButtonTextActive: {
    color: 'white',
  },
  videoContainer: {
    aspectRatio: 16 / 9,
    backgroundColor: '#000',
    borderRadius: 8,
    overflow: 'hidden',
  },
  video: {
    flex: 1,
  },
  testButton: {
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
  },
  testButtonText: {
    color: 'white',
    textAlign: 'center',
    fontWeight: 'bold',
    fontSize: 16,
  },
  resultsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  resultsButtons: {
    flexDirection: 'row',
  },
  clearButton: {
    backgroundColor: '#FF5722',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    marginRight: 8,
  },
  clearButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  exportButton: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  exportButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  noResults: {
    fontStyle: 'italic',
    color: '#666',
    textAlign: 'center',
    padding: 20,
  },
  resultItem: {
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    paddingVertical: 8,
  },
  resultTime: {
    fontSize: 12,
    color: '#666',
  },
  resultTest: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginVertical: 2,
  },
  resultStatus: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  resultPassed: {
    color: '#4CAF50',
  },
  resultFailed: {
    color: '#F44336',
  },
  instructions: {
    fontSize: 14,
    lineHeight: 20,
    color: '#555',
  },
  bold: {
    fontWeight: 'bold',
  },
});

export default ManualAdaptiveBitrateTest;
