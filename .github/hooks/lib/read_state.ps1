# Shared helper: reads .github/shared/project_state.md relative to the hooks/lib/ directory.
# Falls back to legacy shared/project_state.md during transition.
# Usage: . "$PSScriptRoot\read_state.ps1"
#        $content = Get-ProjectState

function Get-ProjectState {
    $root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
    $primaryPath = Join-Path $root ".github\shared\project_state.md"
    $fallbackPath = Join-Path $root "shared\project_state.md"

    $path = if (Test-Path $primaryPath) { $primaryPath } else { $fallbackPath }

    if (Test-Path $path) {
        Get-Content $path -Raw -Encoding UTF8
    } else {
        ""
    }
}
