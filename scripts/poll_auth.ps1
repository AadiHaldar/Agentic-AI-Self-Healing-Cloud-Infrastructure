$clientId = "178c6fc778ccc68e1d6a"
$deviceCode = "3e75af28f28f1bbba60e8c663856349c4cd6a003"
$pollUrl = "https://github.com/login/oauth/access_token"

Write-Host "Polling for GitHub authentication..."
while ($true) {
    $body = @{
        client_id = $clientId
        device_code = $deviceCode
        grant_type = "urn:ietf:params:oauth:grant-type:device_code"
    }
    
    $response = Invoke-RestMethod -Uri $pollUrl -Method Post -Body $body -Headers @{ "Accept" = "application/json" }
    
    if ($response.access_token) {
        Write-Host "Authentication successful! Pushing to GitHub..."
        $token = $response.access_token
        
        # Configure git temporarily with the token
        git remote set-url origin "https://oauth2:$($token)@github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure.git"
        
        git push origin main
        git push origin phase-2
        
        Write-Host "Push complete!"
        exit 0
    }
    
    if ($response.error -eq "authorization_pending") {
        # Still waiting
        Start-Sleep -Seconds 6
    } elseif ($response.error -eq "slow_down") {
        Start-Sleep -Seconds 10
    } else {
        Write-Host "Error: $($response.error)"
        exit 1
    }
}
