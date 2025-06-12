# Monitor Kafka topics for continuous learning pipeline
# PowerShell script to watch message flow

param(
    [string]$Topic = "all",
    [int]$MaxMessages = 10
)

$KAFKA_CONTAINER = "kafka"

function Watch-KafkaTopic {
    param($TopicName, $MaxMessages)
    
    Write-Host "`n=== Monitoring $TopicName topic ===" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop monitoring`n"
    
    docker exec -it $KAFKA_CONTAINER kafka-console-consumer.sh `
        --bootstrap-server localhost:9092 `
        --topic $TopicName `
        --from-beginning `
        --max-messages $MaxMessages `
        --property print.timestamp=true `
        --property print.key=true
}

function Show-TopicInfo {
    param($TopicName)
    
    Write-Host "`n--- Topic: $TopicName ---" -ForegroundColor Yellow
    
    # Get topic details
    docker exec $KAFKA_CONTAINER kafka-topics.sh `
        --describe `
        --topic $TopicName `
        --bootstrap-server localhost:9092
    
    # Get consumer group info
    Write-Host "`nConsumer groups:"
    docker exec $KAFKA_CONTAINER kafka-consumer-groups.sh `
        --bootstrap-server localhost:9092 `
        --list | Where-Object { $_ -like "*$TopicName*" -or $_ -like "*hard*" -or $_ -like "*annotation*" -or $_ -like "*training*" }
}

Write-Host "=== Kafka Continuous Learning Pipeline Monitor ===" -ForegroundColor Green

if ($Topic -eq "all") {
    Write-Host "`nAvailable topics related to continuous learning:"
    $topics = @("hard-examples", "labeled-examples", "model-updates", "camera.events")
    
    foreach ($topicName in $topics) {
        try {
            Show-TopicInfo $topicName
        } catch {
            Write-Host "Topic $topicName not found or not accessible" -ForegroundColor Red
        }
    }
    
    Write-Host "`nChoose a topic to monitor:"
    Write-Host "1. hard-examples (low-confidence detections)"
    Write-Host "2. labeled-examples (human-corrected annotations)"
    Write-Host "3. model-updates (new trained models)"
    Write-Host "4. camera.events (all camera events)"
    Write-Host "5. Monitor all topics simultaneously"
    
    $choice = Read-Host "`nEnter choice (1-5)"
    
    switch ($choice) {
        "1" { Watch-KafkaTopic "hard-examples" $MaxMessages }
        "2" { Watch-KafkaTopic "labeled-examples" $MaxMessages }
        "3" { Watch-KafkaTopic "model-updates" $MaxMessages }
        "4" { Watch-KafkaTopic "camera.events" $MaxMessages }
        "5" {
            Write-Host "`nStarting multiple monitors..."
            Write-Host "Opening separate windows for each topic..."
            
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$PSCommandPath' -Topic hard-examples -MaxMessages $MaxMessages"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$PSCommandPath' -Topic labeled-examples -MaxMessages $MaxMessages"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$PSCommandPath' -Topic model-updates -MaxMessages $MaxMessages"
        }
        default { Write-Host "Invalid choice" -ForegroundColor Red }
    }
} else {
    Watch-KafkaTopic $Topic $MaxMessages
}
