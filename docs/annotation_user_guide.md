# Annotation User Guide

## Overview

The Annotation Frontend provides a web-based interface for human annotators to review and correct AI detection results. This human-in-the-loop process is essential for continuous learning and improving the accuracy of the surveillance system's AI models.

## Accessing the Annotation Interface

1. **Open your web browser** and navigate to: `http://localhost:8011`
2. **Log in** with your annotator credentials
3. You'll see the main annotation dashboard with pending examples

## Interface Overview

The annotation interface consists of several key areas:

```
┌─────────────────────────────────────────────────────────────┐
│                   🏷️ Hard Example Annotation Tool            │
├─────────────────┬───────────────────────────────────────────┤
│   📊 Stats      │              🖼️ Image Canvas              │
│   & Queue       │                                           │
│                 │  ┌─────────────────────────────────────┐  │
│   📋 Example    │  │                                     │  │
│   List          │  │        Annotation Area              │  │
│                 │  │                                     │  │
│                 │  └─────────────────────────────────────┘  │
│                 │                                           │
├─────────────────┼───────────────────────────────────────────┤
│                 │   🔧 Annotation Tools & Controls          │
└─────────────────┴───────────────────────────────────────────┘
```

### 1. Statistics Panel (Top Left)
- **Pending Count**: Number of examples waiting for annotation
- **Queue Status**: Real-time updates of annotation progress

### 2. Example List (Left Sidebar)
- **Pending Examples**: Scrollable list of all examples awaiting annotation
- **Example Cards**: Show camera ID, timestamp, and detection confidence
- **Quick Preview**: Click any card to load that example

### 3. Main Canvas (Center)
- **Image Display**: Shows the frame needing annotation
- **Bounding Boxes**: Visual overlays showing AI detections
- **Interactive Tools**: Click and drag to adjust bounding boxes

### 4. Annotation Controls (Right Panel)
- **Detection Details**: Shows original AI predictions
- **Correction Tools**: Interface to fix incorrect detections
- **Quality Controls**: Options to rate annotation quality
- **Submit/Skip Buttons**: Actions to complete or skip examples

## Step-by-Step Annotation Workflow

### Step 1: Select an Example

1. **Review the example list** in the left sidebar
2. **Look for indicators** like confidence scores and timestamps
3. **Click on an example card** to load it in the main canvas

```
Example Card Layout:
┌─────────────────────────────┐
│ 📹 Front Door Camera        │
│ ⏰ 2025-06-16 11:30:00     │
│ ⚠️ Low Confidence: Person   │
│ 📊 Confidence: 0.45        │
└─────────────────────────────┘
```

### Step 2: Review the Image and Detections

1. **Examine the loaded image** in the central canvas area
2. **Review existing bounding boxes** (shown as red rectangles)
3. **Check detection labels** and confidence scores
4. **Identify any issues**:
   - Incorrect classifications
   - Missing detections
   - False positive detections
   - Poorly positioned bounding boxes

### Step 3: Correct the Detections

#### 3.1 Validate Correct Detections
- **Check the checkbox** next to correct detections
- **Correct detections** will be marked as validated

#### 3.2 Fix Incorrect Classifications
1. **Uncheck incorrect detections**
2. **Select the correct class** from the dropdown menu:
   - `Person` - Human beings
   - `Vehicle` - Cars, trucks, motorcycles
   - `Face` - Human faces (for access control)
   - `Object` - Other objects of interest

#### 3.3 Adjust Bounding Boxes (if needed)
1. **Click and drag** the corners of bounding boxes
2. **Ensure boxes tightly fit** around the detected objects
3. **Make boxes rectangular** and properly aligned

### Step 4: Add Missing Detections

If the AI missed obvious detections:

1. **Click "Add Detection"** (if available in interface)
2. **Draw a new bounding box** around the missed object
3. **Select the appropriate class** from the dropdown
4. **Set confidence level** based on how obvious the detection is

### Step 5: Rate the Annotation Quality

1. **Select a quality score** from the dropdown:
   - **Excellent (1.0)**: Perfect image, clear detections
   - **Good (0.8)**: Good quality, minor issues
   - **Fair (0.6)**: Acceptable quality, some challenges
   - **Poor (0.4)**: Difficult conditions, low quality

2. **Add notes** (optional) in the text area:
   - Explain difficult cases
   - Note environmental conditions
   - Mention any special circumstances

### Step 6: Submit or Skip

#### Submit Annotation
1. **Fill in your Annotator ID** (required)
2. **Review all corrections** one final time
3. **Click "Submit"** to save the annotation
4. **Confirmation** will appear when successfully saved

#### Skip Example
1. **Click "Skip"** if the example is:
   - Too unclear to annotate accurately
   - Contains sensitive content
   - Has technical issues
2. **Skipped examples** are removed from the queue

## Annotation Guidelines

### Best Practices

#### 1. Accuracy Over Speed
- **Take time** to make accurate corrections
- **Double-check** classifications before submitting
- **When in doubt**, err on the side of caution

#### 2. Bounding Box Guidelines
- **Tight fit**: Boxes should closely surround objects
- **Complete coverage**: Include the entire object
- **Avoid overlap**: Minimize overlapping boxes when possible
- **Sharp edges**: Make boxes as precise as possible

#### 3. Classification Guidelines

**Person Detection:**
- Include full human figures
- Include partial humans if torso/head visible
- Exclude distant figures that are unclear
- Include people in various poses and activities

**Vehicle Detection:**
- Cars, trucks, motorcycles, bicycles
- Include parked and moving vehicles
- Exclude extremely distant or unclear vehicles
- Include vehicles partially outside frame

**Face Detection:**
- Clear, frontal or semi-frontal faces
- Minimum resolution for recognition quality
- Exclude profiles or extremely angled faces
- Include faces with accessories (glasses, hats)

#### 4. Quality Considerations

**Mark as Excellent when:**
- Clear, well-lit image
- Objects are easily distinguishable
- No ambiguity in classifications
- High-resolution details visible

**Mark as Poor when:**
- Very dark or overexposed image
- Heavy motion blur
- Objects barely visible
- Multiple classification ambiguities

### Common Scenarios

#### Scenario 1: Low Confidence Person Detection
```
Original: Person (confidence: 0.45)
Action: Verify if it's actually a person
- If yes: ✅ Check "is_correct"
- If no: ❌ Uncheck and select correct class
```

#### Scenario 2: Multiple Overlapping Objects
```
Challenge: Person and vehicle overlapping
Action: 
1. Separate bounding boxes if possible
2. Prioritize the primary object
3. Add notes about overlap
```

#### Scenario 3: Partial Objects
```
Challenge: Person/vehicle partially outside frame
Action:
1. Include if >50% visible
2. Fit box to visible portion
3. Classify based on visible parts
```

#### Scenario 4: Uncertain Classifications
```
Challenge: Object could be person or mannequin
Action:
1. Use context clues (location, movement)
2. If still uncertain, add detailed notes
3. Choose most likely classification
```

## Interface Controls Reference

### Canvas Controls
- **Zoom**: Mouse wheel or +/- buttons
- **Pan**: Click and drag background
- **Select Box**: Click on bounding box
- **Resize Box**: Drag corner handles
- **Move Box**: Drag center of box

### Keyboard Shortcuts
- **Enter**: Submit current annotation
- **Escape**: Skip current example
- **Space**: Toggle between tools
- **Delete**: Remove selected bounding box
- **Tab**: Switch between detection boxes

### Detection Panel
```
Original Detections:
┌─────────────────────────────┐
│ ✅ Person (0.89)           │
│ ❌ Vehicle (0.23) → Person │
│ ✅ Face (0.76)             │
└─────────────────────────────┘

Corrected Labels:
┌─────────────────────────────┐
│ Person ✓                   │
│ Person (corrected)         │
│ Face ✓                     │
└─────────────────────────────┘
```

### Quality Rating Panel
```
┌─────────────────────────────┐
│ Annotator ID: [user-123]   │
│ Quality: [Excellent ▼]     │
│ Notes: [Optional text...]   │
│                             │
│ [Skip] [Submit Annotation]  │
└─────────────────────────────┘
```

## Troubleshooting

### Common Issues

#### "Cannot load example"
- **Cause**: Network connectivity or server issues
- **Solution**: Refresh page and try again
- **Escalate**: Contact admin if persistent

#### "Image not displaying"
- **Cause**: Browser compatibility or missing image data
- **Solution**: Try different browser (Chrome recommended)
- **Workaround**: Use placeholder data for annotation

#### "Annotation won't submit"
- **Cause**: Missing required fields or network timeout
- **Solution**: 
  1. Check Annotator ID is filled
  2. Verify internet connection
  3. Try submitting again

#### "Bounding boxes not responding"
- **Cause**: JavaScript errors or browser issues
- **Solution**: 
  1. Refresh the page
  2. Clear browser cache
  3. Disable browser extensions

### Performance Tips

#### For Large Images
- Use zoom controls to focus on specific areas
- Work systematically from top to bottom
- Save frequently to avoid losing work

#### For Many Detections
- Process obvious corrections first
- Group similar objects together
- Use batch operations when available

#### For Slow Loading
- Check internet connection speed
- Close other browser tabs
- Clear browser cache

## Data Privacy & Security

### Privacy Guidelines
- **No screenshots** of annotation interface
- **Secure workstation** access only
- **Log out** when finished
- **Report suspicious content** immediately

### Data Handling
- All annotations are **encrypted in transit**
- **Audit trails** track all annotation activities
- **Access logs** monitor user sessions
- **Automatic session timeout** after inactivity

### Compliance
- **GDPR compliance** for EU data subjects
- **Data retention** policies automatically enforced
- **Right to be forgotten** requests handled automatically
- **Audit logging** for regulatory compliance

## Getting Help

### In-App Support
- **Help tooltips**: Hover over interface elements
- **Status indicators**: Check connection and system status
- **Error messages**: Read carefully for specific guidance

### Contact Support
- **Technical Issues**: support@surveillance-system.com
- **Training Questions**: training@surveillance-system.com
- **Urgent Issues**: Call emergency support line

### Training Resources
- **Video tutorials**: Available in help section
- **Practice datasets**: Safe examples for learning
- **Best practices guide**: Detailed annotation standards
- **Quality metrics**: Track your annotation accuracy

## Performance Metrics

Your annotation performance is tracked to ensure quality:

### Quality Metrics
- **Accuracy Rate**: Percentage of correct annotations
- **Speed**: Average time per annotation
- **Consistency**: Agreement with other annotators
- **Completeness**: Percentage of examples fully annotated

### Feedback Loop
- **Weekly reports**: Summary of your annotation statistics
- **Quality feedback**: Specific areas for improvement
- **Best practices**: Tips based on your annotation patterns
- **Recognition**: Outstanding annotator achievements

This user guide ensures that human annotators can effectively contribute to the continuous learning system while maintaining high quality standards and proper data handling procedures.
