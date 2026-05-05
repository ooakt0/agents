# Hook: on_stop.ps1
# Event: Stop (fires when Claude finishes a response)
# Purpose: Check for open active tasks in project_state.md and remind the agent to sync state.
# Always exits 0 — never blocks on Stop.

$ErrorActionPreference = "SilentlyContinue"

try {
    # Load the shared state reader
    . "$PSScriptRoot\lib\read_state.ps1"
    $stateContent = Get-ProjectState

    if ([string]::IsNullOrWhiteSpace($stateContent)) { exit 0 }

    # Check for active tasks (the 🏗️ ACTIVE emoji marker used in project_state.md)
    if ($stateContent -like "*🏗️ ACTIVE*") {
        Write-Output ""
        Write-Output "[REMINDER] There is an active task (🏗️ ACTIVE) in .github/shared/project_state.md."
        Write-Output "           Update the 'Last Sync' timestamp before ending this session."
        Write-Output "           If handing off to another agent, use techLead/handoff_template.md."
    }

    exit 0

} catch {
    exit 0
}
