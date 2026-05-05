# Hook: on_write.ps1
# Event: PostToolUse (Write | Edit)
# Purpose: Scan written/edited content for agent handoff signal phrases and route to the next agent.
# Output (stdout) is injected into Claude's context window as a system note.
# Exit code 2 blocks Claude from continuing (used only for SECURITY FAIL).

$ErrorActionPreference = "Stop"

try {
    # Read JSON from stdin (Claude Code pipes hook data as JSON)
    $rawInput = $input | Out-String
    if ([string]::IsNullOrWhiteSpace($rawInput)) { exit 0 }

    $data = $rawInput | ConvertFrom-Json

    # Guard: payload must have tool_input to proceed
    if (-not $data.PSObject.Properties["tool_input"] -or $null -eq $data.tool_input) { exit 0 }

    # Extract written content — Write tool uses .content, Edit tool uses .new_string
    $content = ""
    if ($data.tool_input.PSObject.Properties["content"]) {
        $content = $data.tool_input.content
    } elseif ($data.tool_input.PSObject.Properties["new_string"]) {
        $content = $data.tool_input.new_string
    }

    # Extract file path for context
    $filePath = ""
    if ($data.tool_input.PSObject.Properties["file_path"]) {
        $filePath = $data.tool_input.file_path
    } elseif ($data.tool_input.PSObject.Properties["path"]) {
        $filePath = $data.tool_input.path
    }

    if ([string]::IsNullOrWhiteSpace($content)) { exit 0 }

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCKING: Security failure — checked first, always exits 2 to halt Claude
    # ─────────────────────────────────────────────────────────────────────────
    if ($content -clike "*SECURITY FAIL:*") {
        $msg = ($content -split "SECURITY FAIL:")[1].Trim().Split("`n")[0].Trim()
        Write-Error "[SECURITY BLOCK] Workflow halted. Violation: $msg"
        Write-Error "@techLead must resolve this before any further work. Do not deliver to user."
        exit 2
    }

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT-TO-AGENT ROUTING (inter-agent boundaries)
    # ─────────────────────────────────────────────────────────────────────────

    # @codeCrafter → @codeReviewer  (via resilience_patterns Output Contract)
    if ($content -like "*Handing off to @codeReviewer*") {
        Write-Output ""
        Write-Output "[WORKFLOW] Handoff to @codeReviewer detected."
        Write-Output "[NEXT] You are now @codeReviewer. Read .github/skills/codeReviewer/complexity_check.md"
        Write-Output "       and begin the complexity check immediately. Do not wait for user input."
        Write-Output "       Chain: complexity_check → naming_audit → dependency_audit → documentation_check"
    }

    # @codeReviewer → @qualityGuard  (via documentation_check Output Contract)
    elseif ($content -like "*Handing off to @qualityGuard*") {
        Write-Output ""
        Write-Output "[WORKFLOW] Handoff to @qualityGuard detected."
        Write-Output "[NEXT] You are now @qualityGuard. Read .github/skills/qualityGuard/write_unit_tests.md"
        Write-Output "       and begin unit test generation immediately. Do not wait for user input."
        Write-Output "       Chain: write_unit_tests → mock_aws_responses → integration_test → load_test → penetration_scan"
    }

    # @qualityGuard → @techLead  (quality gate cleared, ready for AUDIT_RESULT)
    elseif ($content -like "*Quality gate cleared*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @qualityGuard quality gate cleared — all checks passed."
        Write-Output "[NEXT] You are now @techLead. Run AUDIT_RESULT to verify against"
        Write-Output "       .github/shared/standards.md §1-5. If all pass, delegate to @devOps."
        Write-Output "       Use: DELEGATE [devOps] with .github/skills/devOps/pipeline_setup.md"
    }

    # @techLead → @devOps  (after AUDIT_RESULT passes)
    elseif ($content -like "*Handing off to @devOps*") {
        Write-Output ""
        Write-Output "[WORKFLOW] Handoff to @devOps detected."
        Write-Output "[NEXT] You are now @devOps. Read .github/skills/devOps/pipeline_setup.md"
        Write-Output "       and begin CI/CD pipeline setup. Do not wait for user input."
        Write-Output "       Chain: pipeline_setup → environment_promotion → deployment_verification"
    }

    # Any agent → @techLead  (architect approval, devOps verified, or any return)
    elseif ($content -like "*Returning to @techLead*") {
        Write-Output ""
        Write-Output "[WORKFLOW] Agent returning control to @techLead."
        Write-Output "[NEXT] You are now @techLead. Read .github/skills/techLead/system_prompt.md, review the"
        Write-Output "       agent's output, and decide the next action (approve, reject, or delegate)."
    }

    # ─────────────────────────────────────────────────────────────────────────
    # INTRA-ARCHITECT CHAIN REMINDERS
    # ─────────────────────────────────────────────────────────────────────────

    elseif ($content -like "*Observability design complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @architect observability design complete."
        Write-Output "[NEXT] Activate reliability_design skill immediately."
        Write-Output "       Read .github/skills/architect/reliability_design.md and continue."
    }

    elseif ($content -like "*Reliability design complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @architect reliability design complete."
        Write-Output "[NEXT] Activate generate_cdk_boilerplate skill."
        Write-Output "       Read .github/skills/architect/generate_cdk_boilerplate.md and continue."
    }

    # ─────────────────────────────────────────────────────────────────────────
    # INTRA-AGENT CHAIN REMINDERS (reinforce skill-level chaining)
    # ─────────────────────────────────────────────────────────────────────────

    elseif ($content -like "*Cleared for implementation*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @architect security audit passed — implementation unblocked."
        Write-Output "[NEXT] You are now @codeCrafter. Read the handoff in .github/skills/techLead/handoff_template.md"
        Write-Output "       and begin with .github/skills/codeCrafter/implement_logic.md."
    }

    elseif ($content -like "*Resilience patterns complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @codeCrafter resilience patterns applied."
        Write-Output "[NEXT] Hand off to @codeReviewer by writing the required phrase."
    }

    elseif ($content -like "*Dependency audit passed*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @codeReviewer dependency audit passed."
        Write-Output "[NEXT] Activate documentation_check skill immediately."
        Write-Output "       Read .github/skills/codeReviewer/documentation_check.md and continue."
    }

    elseif ($content -like "*Integration tests complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @qualityGuard integration tests complete."
        Write-Output "[NEXT] Activate load_test skill immediately."
        Write-Output "       Read .github/skills/qualityGuard/load_test.md and continue."
    }

    elseif ($content -like "*Load tests complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @qualityGuard load tests complete."
        Write-Output "[NEXT] Activate penetration_scan skill immediately."
        Write-Output "       Read .github/skills/qualityGuard/penetration_scan.md and continue."
    }

    elseif ($content -like "*Pipeline configured*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @devOps pipeline configured."
        Write-Output "[NEXT] Activate environment_promotion skill immediately."
        Write-Output "       Read .github/skills/devOps/environment_promotion.md and continue."
    }

    elseif ($content -like "*Environment promotion complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @devOps environment promotion complete."
        Write-Output "[NEXT] Activate deployment_verification skill immediately."
        Write-Output "       Read .github/skills/devOps/deployment_verification.md and continue."
    }

    # @techLead change analysis complete → impact assessment
    elseif ($content -like "*Change analysis complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @techLead change analysis complete."
        Write-Output "[NEXT] Activate impact_assessment skill immediately."
        Write-Output "       Read .github/skills/techLead/impact_assessment.md and continue."
    }

    # @techLead impact assessment complete → begin delegation
    elseif ($content -like "*Impact assessment complete*") {
        Write-Output ""
        Write-Output "[WORKFLOW] @techLead impact assessment complete."
        Write-Output "[NEXT] Produce the filled handoff template for the first agent in the chain."
        Write-Output "       Use .github/skills/techLead/handoff_template.md. Include 'Shortened Chain' and 'Skipped' fields."
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STATE CHANGE MONITOR
    # ─────────────────────────────────────────────────────────────────────────

    # Check if project_state.md was written with a completed task
    if ($filePath -like "*project_state.md*" -and $content -like "*✅ DONE*") {
        Write-Output ""
        Write-Output "[STATE] project_state.md updated with completed task(s)."
        Write-Output "       @techLead: verify against .github/shared/standards.md §1-5 before closing."
    }

    exit 0

} catch {
    # Non-blocking: log the error but don't interrupt Claude's workflow
    Write-Host "[HOOK WARNING] on_write.ps1 encountered an error: $($_.Exception.Message)"
    exit 1
}
