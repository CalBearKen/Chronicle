# Check if Docker is running
if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    Start-Sleep -Seconds 30
}

# Verify Docker service
$dockerService = Get-Service "Docker Desktop Service" -ErrorAction SilentlyContinue
if (-not $dockerService.Status -eq "Running") {
    Write-Host "Docker service not running. Starting..."
    Start-Service "Docker Desktop Service"
    Start-Sleep -Seconds 15
}

# Verify container status
$containerStatus = docker inspect -f '{{.State.Running}}' rss_mysql 2>$null
if (-not $containerStatus -eq "true") {
    Write-Host "Starting MySQL container..."
    docker-compose -f "C:\Projects\Chronicle\docker-compose.yml" up -d
    Start-Sleep -Seconds 10
}

# Run the scraper
python "C:\Projects\Chronicle\batch_rss_scraper.py"
