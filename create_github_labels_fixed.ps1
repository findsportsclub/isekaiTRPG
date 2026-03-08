param(
    [Parameter(Mandatory=$true)]
    [string]$Repo
)

$ErrorActionPreference = "Stop"

$desired = @(
    @{ Name="P0"; Color="B60205"; Description="highest-priority" },
    @{ Name="P1"; Color="D93F0B"; Description="mvp-required" },
    @{ Name="P2"; Color="FBCA04"; Description="post-mvp" },

    @{ Name="frontend"; Color="1D76DB"; Description="frontend" },
    @{ Name="backend"; Color="5319E7"; Description="backend" },
    @{ Name="db"; Color="0E8A16"; Description="database" },
    @{ Name="api"; Color="006B75"; Description="api" },
    @{ Name="ui"; Color="C2E0C6"; Description="ui-ux" },
    @{ Name="game-logic"; Color="7057FF"; Description="game-logic" },
    @{ Name="infra"; Color="8B5CF6"; Description="infrastructure" },
    @{ Name="docs"; Color="0075CA"; Description="documentation" },

    @{ Name="todo"; Color="D4C5F9"; Description="todo" },
    @{ Name="in-progress"; Color="0052CC"; Description="in-progress" },
    @{ Name="review"; Color="5319E7"; Description="review" },
    @{ Name="blocked"; Color="B60205"; Description="blocked" },
    @{ Name="done"; Color="0E8A16"; Description="done" }
)

$existingJson = gh label list --repo $Repo --limit 500 --json name
$existing = @{}
if ($existingJson) {
    ($existingJson | ConvertFrom-Json) | ForEach-Object { $existing[$_.name] = $true }
}

foreach ($lbl in $desired) {
    if ($existing.ContainsKey($lbl.Name)) {
        Write-Host "label exists: $($lbl.Name)"
    } else {
        gh label create $lbl.Name --repo $Repo --color $lbl.Color --description $lbl.Description
        Write-Host "created: $($lbl.Name)"
    }
}

Write-Host "All labels processed for $Repo"