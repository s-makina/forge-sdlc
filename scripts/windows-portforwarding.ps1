<#
.\scripts\windows-portforwarding.ps1 -StagingIP 41.77.8.234 -Action Add
.SYNOPSIS
    Set up, remove, or list Windows port forwarding to the ForgeSDLC staging server.
.DESCRIPTION
    Uses netsh interface portproxy to forward localhost ports to the staging server.
    This lets you access ForgeSDLC services from Windows as if they were local:
      http://localhost:8082/login   -> staging:8082 (proxy)
      http://localhost:8000/health  -> staging:8000 (api)
    etc.
.REQUIREMENTS
    - Run PowerShell as Administrator
    - Windows machine must have network reachability to the staging server IP
    - Staging server firewall/security group must allow inbound from your Windows IP
.PARAMETER StagingIP
    IP address of the staging server (e.g. 203.0.113.45 or 10.0.0.50).
.PARAMETER Action
    Add   - create port forwarding rules
    Remove - delete port forwarding rules
    List   - show all active portproxy rules
    Status - show only ForgeSDLC-related rules
.EXAMPLE
    .\scripts\windows-portforwarding.ps1 -StagingIP 203.0.113.45 -Action Add
.EXAMPLE
    .\scripts\windows-portforwarding.ps1 -StagingIP 203.0.113.45 -Action Remove
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$StagingIP,

    [ValidateSet('Add', 'Remove', 'List', 'Status')]
    [string]$Action = 'Add'
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

function Test-Administrator {
    $currentUser = New-Object Security.Principal.WindowsPrincipal $([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ---- Guard: require Administrator ----
if (-not (Test-Administrator)) {
    Write-Error 'This script must be run as Administrator.'
    Write-Host '  Right-click PowerShell and select "Run as Administrator", then re-run this script.'
    exit 1
}

# ---- Actions ----
switch ($Action) {
    'Add' {
        Write-Host "Adding ForgeSDLC port forwarding rules to staging IP $StagingIP ..." -ForegroundColor Cyan
        foreach ($m in $PortMappings) {
            netsh interface portproxy add v4tov4 `
                listenport=$m.Local listenaddress=127.0.0.1 `
                connectport=$m.Remote connectaddress=$StagingIP
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  OK   127.0.0.1:$($m.Local)  ->  ${StagingIP}:$($m.Remote)  ($($m.Desc))" -ForegroundColor Green
            } else {
                Write-Warning "  FAIL 127.0.0.1:$($m.Local)  ->  ${StagingIP}:$($m.Remote)  ($($m.Desc))"
            }
        }
        Write-Host "
Done. You can now access services via http://localhost:<port>" -ForegroundColor Cyan
        Write-Host "  Example: http://localhost:8082/login"
    }

    'Remove' {
        Write-Host "Removing ForgeSDLC port forwarding rules ..." -ForegroundColor Cyan
        foreach ($m in $PortMappings) {
            netsh interface portproxy delete v4tov4 listenport=$m.Local listenaddress=127.0.0.1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Removed 127.0.0.1:$($m.Local)" -ForegroundColor Green
            } else {
                Write-Warning "  Could not remove 127.0.0.1:$($m.Local) (may not exist)"
            }
        }
    }

    'List' {
        netsh interface portproxy show all
    }

    'Status' {
        Write-Host "ForgeSDLC port forwarding rules:" -ForegroundColor Cyan
        netsh interface portproxy show all | Select-String '127.0.0.1' | ForEach-Object { Write-Host "  $_" }
    }
}

# ---- Quick connectivity hints ----
if ($Action -eq 'Add') {
    Write-Host "
Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Test from Windows PowerShell:"
    Write-Host "     curl http://localhost:8082/login"
    Write-Host "     curl http://localhost:8000/health"
    Write-Host "  2. If connection fails, ensure your Windows firewall allows outbound to $StagingIP"
    Write-Host "  3. Ensure the staging server security group allows inbound from your Windows IP on the forwarded ports."
}