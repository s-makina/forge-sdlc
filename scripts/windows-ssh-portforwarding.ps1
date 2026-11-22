<#
.\scripts\windows-ssh-portforwarding.ps1 -StagingUser icamadmin -StagingIP 41.77.8.234 -SshPort 9022 -Action Start
.SYNOPSIS
    Set up SSH local port forwarding from Windows to the ForgeSDLC staging server.
.DESCRIPTION
    Uses SSH (-L) to forward localhost ports on Windows through the SSH tunnel
    to services running on the staging server. This works even when the server's
    firewall blocks direct inbound connections, because the traffic rides inside
    the SSH connection on port 9022.

    Keep this script running in one PowerShell window while you access services
    in another window / browser.
.REQUIREMENTS
    - OpenSSH client installed on Windows (built-in on Windows 10/11)
    - SSH access to the staging server (ssh -p 9022 icamadmin@41.77.8.234)
    - ForgeSDLC stack running on staging
.PARAMETER StagingUser
    SSH username on the staging server.
.PARAMETER StagingIP
    IP address or hostname of the staging server.
.PARAMETER SshPort
    SSH port on the staging server.
.PARAMETER Action
    Start   - create the SSH tunnel and keep it running
    Stop    - stop any running ssh tunnel processes
    Status  - check if ssh is available
.EXAMPLE
    .\scripts\windows-ssh-portforwarding.ps1 -StagingUser icamadmin -StagingIP 41.77.8.234 -SshPort 9022 -Action Start
.EXAMPLE
    .\scripts\windows-ssh-portforwarding.ps1 -Action Stop
#>
[CmdletBinding()]
param(
    [string]$StagingUser = 'icamadmin',
    [string]$StagingIP = '41.77.8.234',
    [int]$SshPort = 9022,
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Start'
)

# LocalPort -> RemotePort on staging -> Description
$PortMappings = @(
    @{ Local = 8082; Remote = 8082; Desc = 'Proxy / Login' },
    @{ Local = 8000; Remote = 8000; Desc = 'API' },
    @{ Local = 8001; Remote = 8001; Desc = 'Execution Manager' },
    @{ Local = 8002; Remote = 8002; Desc = 'Orchestrator' },
    @{ Local = 8083; Remote = 8083; Desc = 'Temporal UI' },
    @{ Local = 4000; Remote = 4000; Desc = 'LiteLLM' },
    @{ Local = 5433; Remote = 5433; Desc = 'Postgres' },
    @{ Local = 6380; Remote = 6380; Desc = 'Redis' }
)

# ---- Build SSH -L arguments ----
$SshArgs = @("-p", $SshPort, "-N")
foreach ($m in $PortMappings) {
    $SshArgs += "-L", "$($m.Local):localhost:$($m.Remote)"
}
$SshArgs += "$($StagingUser)@$($StagingIP)"

function Test-SshAvailable {
    $cmd = Get-Command ssh -ErrorAction SilentlyContinue
    return $null -ne $cmd
}

# ---- Actions ----
switch ($Action) {
    'Status' {
        if (Test-SshAvailable) {
            Write-Host 'OpenSSH client is available.' -ForegroundColor Green
        } else {
            Write-Error 'OpenSSH client not found. Install it via:
  Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0'
        }
    }

    'Start' {
        if (-not (Test-SshAvailable)) {
            Write-Error 'OpenSSH client not found. Install it via:
  Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0'
            exit 1
        }

        Write-Host "Starting SSH tunnel to ${StagingUser}@${StagingIP}:${SshPort} ..." -ForegroundColor Cyan
        Write-Host "Forwarding ports:" -ForegroundColor Cyan
        foreach ($m in $PortMappings) {
            Write-Host "  localhost:$($m.Local)  ->  ${StagingUser}@${StagingIP}:localhost:$($m.Remote)  ($($m.Desc))"
        }
        Write-Host "
Keep this window open. Press Ctrl+C to stop the tunnel.
Then in another window, visit: http://localhost:8082/login" -ForegroundColor Cyan

        ssh @SshArgs
    }

    'Stop' {
        Write-Host 'Stopping SSH tunnel processes ...' -ForegroundColor Cyan
        Get-Process ssh -ErrorAction SilentlyContinue | Where-Object { $_.Path -match 'ssh' } | Stop-Process -Force
        Write-Host 'Done.' -ForegroundColor Green
    }
}

# ---- Quick test hints ----
if ($Action -eq 'Start') {
    Write-Host "
Once the tunnel is up, test from another PowerShell window:
  curl.exe http://localhost:8082/login
  curl.exe http://localhost:8000/health" -ForegroundColor Cyan
}