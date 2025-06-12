# Create Kafka topics for continuous learning pipeline
# PowerShell script for Windows

$KAFKA_CONTAINER = "kafka"

Write-Host "Creating Kafka topics for continuous learning pipeline..." -ForegroundColor Green

# Hard examples topic for low-confidence detections
Write-Host "Creating hard-examples topic..."
docker exec $KAFKA_CONTAINER kafka-topics.sh `
    --create `
    --topic hard-examples `
    --bootstrap-server localhost:9092 `
    --partitions 3 `
    --replication-factor 1 `
    --config retention.ms=604800000 `
    --if-not-exists

# Labeled examples topic for human-corrected annotations
Write-Host "Creating labeled-examples topic..."
docker exec $KAFKA_CONTAINER kafka-topics.sh `
    --create `
    --topic labeled-examples `
    --bootstrap-server localhost:9092 `
    --partitions 3 `
    --replication-factor 1 `
    --config retention.ms=2592000000 `
    --if-not-exists

# Model updates topic for pushing new trained models
Write-Host "Creating model-updates topic..."
docker exec $KAFKA_CONTAINER kafka-topics.sh `
    --create `
    --topic model-updates `
    --bootstrap-server localhost:9092 `
    --partitions 1 `
    --replication-factor 1 `
    --config retention.ms=86400000 `
    --if-not-exists

Write-Host "Kafka topics created successfully!" -ForegroundColor Green

# List all topics to verify
Write-Host "`nCurrent Kafka topics:" -ForegroundColor Yellow
docker exec $KAFKA_CONTAINER kafka-topics.sh `
    --list `
    --bootstrap-server localhost:9092
