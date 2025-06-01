# Fix Dockerfiles to include shared module
Write-Host "Fixing Dockerfiles to include shared module..."

$services = @(
    "vms_service",
    "edge_service", 
    "ingest_service",
    "rag_service",
    "prompt_service",
    "rulegen_service",
    "notifier",
    "mqtt_kafka_bridge"
)

foreach ($service in $services) {
    $dockerfilePath = "$service\Dockerfile"
    if (Test-Path $dockerfilePath) {
        Write-Host "Updating $dockerfilePath"
        $content = Get-Content $dockerfilePath
        
        # Find the line that copies the service directory
        $newContent = @()
        foreach ($line in $content) {
            $newContent += $line
            
            # After copying requirements, add shared directory copy
            if ($line -match "COPY $service/requirements.txt") {
                $newContent += "# Copy shared module"
                $newContent += "COPY shared/ /app/shared/"
            }
        }
        
        $newContent | Set-Content $dockerfilePath
        Write-Host "Updated $dockerfilePath"
    }
}

Write-Host "All Dockerfiles updated!"
