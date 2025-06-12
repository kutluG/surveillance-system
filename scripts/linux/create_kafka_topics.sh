#!/bin/bash
# Create Kafka topics for continuous learning pipeline

KAFKA_CONTAINER="kafka"

# Hard examples topic for low-confidence detections
docker exec $KAFKA_CONTAINER kafka-topics.sh \
    --create \
    --topic hard-examples \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1 \
    --config retention.ms=604800000 \
    --if-not-exists

# Labeled examples topic for human-corrected annotations
docker exec $KAFKA_CONTAINER kafka-topics.sh \
    --create \
    --topic labeled-examples \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1 \
    --config retention.ms=2592000000 \
    --if-not-exists

# Model updates topic for pushing new trained models
docker exec $KAFKA_CONTAINER kafka-topics.sh \
    --create \
    --topic model-updates \
    --bootstrap-server localhost:9092 \
    --partitions 1 \
    --replication-factor 1 \
    --config retention.ms=86400000 \
    --if-not-exists

echo "Kafka topics created successfully!"

# List all topics to verify
echo "Current Kafka topics:"
docker exec $KAFKA_CONTAINER kafka-topics.sh \
    --list \
    --bootstrap-server localhost:9092
