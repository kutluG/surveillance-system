# Manual Test Cases for HLS Adaptive Bitrate Video Player

## Test Suite: HLS Adaptive Bitrate Functionality

### Prerequisites
- React Native development environment set up
- Mobile device or emulator with network connectivity
- Access to HLS test streams (or mock HLS master playlist)

### Test Data
Use these test HLS streams for manual testing:

**Test Stream 1 - Multi-bitrate HLS**
```
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
```

**Test Stream 2 - Apple HLS Sample**
```
https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8
```

**Mock Master Playlist** (for local testing):
```m3u8
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=720x480,CODECS="avc1.42001e,mp4a.40.2"
low/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2560000,RESOLUTION=960x640,CODECS="avc1.42001e,mp4a.40.2"
medium/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=7680000,RESOLUTION=1920x1280,CODECS="avc1.42001e,mp4a.40.2"
high/playlist.m3u8
```

---

## Test Case 1: Auto Quality Switching Verification

### Objective
Verify that the video player automatically switches between quality levels based on network conditions.

### Test Steps

1. **Setup**
   - Open the CameraView component with a multi-bitrate HLS stream
   - Ensure "Auto Quality" toggle is ON (default state)
   - Connect device to WiFi with good bandwidth

2. **Initial State Verification**
   - ✅ Video starts playing
   - ✅ Quality indicator shows "AUTO"
   - ✅ Video loads without buffering issues
   - ✅ Initial quality should be medium-high based on network

3. **Network Condition Simulation**
   - **High Bandwidth Test:**
     - Ensure strong WiFi connection
     - ✅ Player should select highest available quality
     - ✅ Video plays smoothly without buffering
     - ✅ Quality indicator remains "AUTO"

   - **Medium Bandwidth Test:**
     - Limit network bandwidth (use network throttling tools)
     - ✅ Player should adapt to medium quality within 10-15 seconds
     - ✅ Video continues playing without interruption
     - ✅ Minimal buffering during quality transition

   - **Low Bandwidth Test:**
     - Further limit bandwidth or switch to mobile data
     - ✅ Player should switch to lowest quality
     - ✅ Video remains playable
     - ✅ No excessive buffering

4. **Recovery Test**
   - Restore high bandwidth connection
   - ✅ Player should gradually switch back to higher quality
   - ✅ Smooth transition without playback interruption

### Expected Results
- Video quality adapts automatically to network conditions
- No playback interruptions during quality switches
- Quality indicator consistently shows "AUTO"
- Buffer health remains stable across quality changes

### Pass Criteria
- [ ] All network condition tests pass
- [ ] Quality switches happen within reasonable time (10-15 seconds)
- [ ] No video freezing or artifacts during transitions
- [ ] Buffer levels remain healthy (minimal buffering)

---

## Test Case 2: Manual 360p Quality Selection

### Objective
Verify manual quality selection works correctly, specifically testing 360p selection and persistence.

### Test Steps

1. **Setup**
   - Open CameraView with multi-bitrate HLS stream
   - Video should be playing with Auto Quality enabled

2. **Access Quality Settings**
   - Tap on the video to show controls
   - ✅ Video controls appear
   - Tap on the quality/settings button (HD icon)
   - ✅ Quality selection modal opens

3. **Quality Modal Verification**
   - ✅ Modal shows "Video Quality" title
   - ✅ "Auto Quality" toggle is visible and ON
   - ✅ Quality options are grayed out/disabled
   - ✅ Available quality levels are displayed with bandwidth info

4. **Manual Quality Selection**
   - Turn OFF the "Auto Quality" toggle
   - ✅ Quality options become enabled/selectable
   - ✅ Current auto-selected quality is highlighted
   - Select "360p" quality option
   - ✅ 360p option becomes highlighted/selected
   - ✅ Bandwidth information is shown (e.g., "1280 kbps")
   - Tap "Close" to apply selection

5. **Manual Quality Verification**
   - ✅ Modal closes
   - ✅ Video switches to 360p quality within 5 seconds
   - ✅ Quality indicator shows "360p" instead of "AUTO"
   - ✅ Video continues playing smoothly
   - ✅ Lower quality is visually apparent (less sharp)

6. **Quality Persistence Test**
   - Close and reopen the CameraView component
   - ✅ Component remembers manual quality setting
   - ✅ Auto Quality toggle remains OFF
   - ✅ 360p quality is pre-selected
   - ✅ Video starts playing in 360p quality

7. **Settings Restoration Test**
   - Change to different quality (e.g., 720p)
   - ✅ Quality switches correctly
   - Turn Auto Quality back ON
   - ✅ Player returns to adaptive behavior
   - ✅ Quality indicator shows "AUTO"

### Expected Results
- Manual quality selection overrides auto quality
- 360p quality selection works and is visually apparent
- Quality settings persist across app sessions
- Smooth transitions between manual and auto quality modes

### Pass Criteria
- [ ] Manual quality selection works for all available qualities
- [ ] 360p specifically selects and displays correctly
- [ ] Settings persist after component unmount/remount
- [ ] Quality indicator accurately reflects current mode
- [ ] No playback interruptions during manual quality changes

---

## Test Case 3: User Preference Persistence

### Objective
Verify that user quality preferences are saved to AsyncStorage and restored correctly.

### Test Steps

1. **Initial State**
   - Fresh app install or cleared storage
   - ✅ Auto Quality should be ON by default
   - ✅ No manual quality pre-selected

2. **Set Manual Preference**
   - Disable Auto Quality
   - Select 720p quality
   - Close quality modal
   - ✅ Settings applied correctly

3. **App Restart Test**
   - Force close and restart the app
   - Navigate to CameraView
   - ✅ Auto Quality toggle is OFF
   - ✅ 720p quality is pre-selected
   - ✅ Video starts in 720p quality

4. **Storage Verification**
   - Check AsyncStorage keys:
     - `camera_auto_quality_enabled`: should be "false"
     - `camera_selected_quality`: should be "720p"

### Pass Criteria
- [ ] Preferences persist across app restarts
- [ ] AsyncStorage contains correct values
- [ ] Default values are applied on first use

---

## Test Case 4: Error Handling and Fallback

### Objective
Verify proper error handling for invalid HLS streams and network issues.

### Test Steps

1. **Invalid HLS URL Test**
   - Provide invalid HLS URL to CameraView
   - ✅ Error state is displayed
   - ✅ Retry button is available
   - ✅ No app crashes

2. **Network Failure Test**
   - Start video playback
   - Disconnect network during playback
   - ✅ Error handling activates
   - ✅ Appropriate error message shown
   - Reconnect network and tap retry
   - ✅ Video resumes playback

3. **Malformed Playlist Test**
   - Use corrupted/malformed HLS playlist
   - ✅ Parser handles error gracefully
   - ✅ Fallback to master playlist occurs
   - ✅ Video attempts to play with available options

### Pass Criteria
- [ ] No app crashes on invalid input
- [ ] Clear error messages for users
- [ ] Graceful degradation when possible
- [ ] Retry mechanism works correctly

---

## Test Case 5: Performance and Memory

### Objective
Verify performance characteristics and memory usage.

### Test Steps

1. **Memory Usage Test**
   - Monitor memory usage during quality switches
   - ✅ No significant memory leaks
   - ✅ Memory usage remains stable

2. **CPU Usage Test**
   - Monitor CPU usage during adaptive quality switching
   - ✅ CPU usage remains reasonable
   - ✅ No performance degradation

3. **Battery Usage Test**
   - Extended playback test (30+ minutes)
   - ✅ Battery drain is reasonable
   - ✅ Device doesn't overheat

### Pass Criteria
- [ ] Memory usage stays within reasonable bounds
- [ ] CPU usage doesn't spike during quality changes
- [ ] Battery drain is comparable to standard video playback

---

## Integration Test Scenarios

### Scenario 1: Multiple Camera Views
- Open multiple CameraView instances
- Verify each maintains independent quality settings
- Test switching between different cameras

### Scenario 2: Background/Foreground Transitions
- Start video playback
- Move app to background
- Return to foreground
- Verify playback resumes correctly with same quality settings

### Scenario 3: Device Rotation
- Test quality settings during device rotation
- Verify fullscreen mode works with quality controls
- Test quality persistence through orientation changes

---

## Test Environment Setup

### Required Tools
- React Native Debugger
- Network throttling tools (Charles Proxy, Chrome DevTools)
- Memory profiling tools
- AsyncStorage inspector

### Test Data Preparation
1. Set up local HLS test server (optional)
2. Prepare various quality HLS streams
3. Configure network throttling scenarios
4. Set up monitoring tools

### Reporting
Document all test results with:
- Screenshots of quality selection UI
- Video quality comparisons
- Performance metrics
- Any bugs or issues found

---

## Success Criteria Summary

The HLS Adaptive Bitrate implementation passes manual testing if:

✅ **Auto Quality Functionality**
- Automatic quality switching based on network conditions
- Smooth transitions without playback interruption
- Proper quality level selection algorithm

✅ **Manual Quality Selection**
- All quality levels selectable manually
- 360p specifically works as expected
- Quality indicator shows correct current setting

✅ **User Preference Persistence**
- Settings saved to AsyncStorage correctly
- Preferences restored on app restart
- Default values work for new users

✅ **Error Handling**
- Graceful handling of network issues
- Proper fallback mechanisms
- No app crashes on invalid input

✅ **Performance**
- Acceptable memory and CPU usage
- No memory leaks during quality switches
- Reasonable battery consumption
