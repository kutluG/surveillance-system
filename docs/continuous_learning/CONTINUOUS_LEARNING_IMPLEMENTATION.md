# Continuous Learning Pipeline Implementation

This document explains how the continuous learning pipeline for hard example collection has been implemented and how to test it.

## Architecture Overview

The continuous learning pipeline consists of these key components:

1. **Edge Service** - Detects low confidence detections and publishes them as hard examples
2. **Hard Example Collector** - Processes camera events and identifies hard examples
3. **Annotation Frontend** - Allows human correction of hard examples
4. **Training Service** - Retrains models on labeled examples

The data flow is as follows:

```
Edge Service ---> Hard Example Collector ---> Annotation Frontend ---> Training Service
    |                    |                         |                        |
 Detects         Collects & Publishes        Human Labeling         Model Retraining
Low-Confidence    to Kafka Topic           Interface & Storage      & Deployment
```

## Implementation Details

### 1. Edge Service Enhancement (`edge_service/inference_with_hard_examples.py`)

The EdgeInference class has been enhanced to:

- Configure confidence thresholds for different object classes
- Detect when inference results fall below thresholds
- Publish hard examples to Kafka for further processing
- Include frame data in hard examples for annotation purposes

### 2. Hard Example Collector (`hard_example_collector/main.py`)

This service:
- Consumes camera events from Kafka
- Filters detections based on configurable confidence thresholds
- Publishes hard examples to the `hard.examples` Kafka topic
- Exposes REST API for configuration and statistics

### 3. Annotation Frontend (`annotation_frontend/main.py`)

The annotation frontend:
- Provides a web UI for human correction of hard examples
- Consumes hard examples from Kafka
- Allows correction of bounding boxes and labels
- Publishes labeled examples to the `labeled.examples` Kafka topic

### 4. Training Service (`training_service/main.py`)

The training service:
- Consumes labeled examples from Kafka
- Schedules regular retraining of models
- Converts updated models to TensorRT format
- Pushes updated models back to edge devices

## Testing the Implementation

### 1. Setup

Run the setup script to install dependencies and configure Kafka topics:

```powershell
.\setup_continuous_learning.ps1 -InstallDependencies -CreateTopics
```

### 2. Testing Hard Example Detection

Test the edge inference hard example detection:

```powershell
python test_hard_examples_fixed.py
```

### 3. Testing the Complete Pipeline

Test the complete pipeline implementation:

```powershell
python test_continuous_learning_pipeline.py
```

### 4. End-to-End Testing with Running Services

Start all services and test the complete flow:

```powershell
# Start all services
docker-compose up -d

# Create Kafka topics
.\create_kafka_topics.ps1

# Run end-to-end test
.\test_continuous_learning.ps1
```

## Configuration

### Confidence Thresholds

Adjust the confidence thresholds in `edge_service/inference_with_hard_examples.py` or via environment variables:

```
PERSON_CONFIDENCE_THRESHOLD=0.6
FACE_CONFIDENCE_THRESHOLD=0.5
VEHICLE_CONFIDENCE_THRESHOLD=0.4
DEFAULT_CONFIDENCE_THRESHOLD=0.5
```

### Kafka Topics

The following Kafka topics are used:

- `camera.events` - All camera events
- `hard.examples` - Low-confidence detections
- `labeled.examples` - Human-corrected annotations
- `model.updates` - New model deployment notifications

## Monitoring

### Check for Hard Examples

```powershell
# Check hard example collector status
Invoke-RestMethod -Uri "http://localhost:8010/stats" -Method GET
```

### Check Annotation Frontend

```powershell
# Check pending examples
Invoke-RestMethod -Uri "http://localhost:8011/api/examples" -Method GET
```

### Check Training Service

```powershell
# Check training status
Invoke-RestMethod -Uri "http://localhost:8012/stats" -Method GET

# Manually trigger training
Invoke-RestMethod -Uri "http://localhost:8012/jobs/start" -Method POST
```

## Future Enhancements

- [ ] Implement active learning strategies to prioritize most informative examples
- [ ] Add support for multi-model training
- [ ] Implement model performance tracking and automatic rollback
- [ ] Add advanced annotation tools (polygon, keypoints)
- [ ] Implement automated quality assessment of annotations
