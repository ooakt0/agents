# Hook: on_task_complete.ps1
# Event: PostToolUse (Write only)
# Purpose: When project_state.md is written with a task marked ✅ DONE, output the
#          full Definition of Done verification checklist for @techLead.

$ErrorActionPreference = "Stop"

try {
    $rawInput = $input | Out-String
    if ([string]::IsNullOrWhiteSpace($rawInput)) { exit 0 }

    $data = $rawInput | ConvertFrom-Json

    # Only act when project_state.md is the file being written
    $filePath = ""
    if ($data.tool_input.PSObject.Properties["file_path"]) {
        $filePath = $data.tool_input.file_path
    } elseif ($data.tool_input.PSObject.Properties["path"]) {
        $filePath = $data.tool_input.path
    }

    if ($filePath -notlike "*project_state.md*") { exit 0 }

    # Check for newly completed tasks
    $content = ""
    if ($data.tool_input.PSObject.Properties["content"]) {
        $content = $data.tool_input.content
    }

    if ([string]::IsNullOrWhiteSpace($content)) { exit 0 }
    if ($content -notlike "*✅ DONE*") { exit 0 }

    # Extract task IDs marked as DONE (look for "T-NNN" on same line as "✅ DONE")
    $doneLines = ($content -split "`n") | Where-Object { $_ -like "*✅ DONE*" }
    $taskIds = $doneLines | ForEach-Object {
        if ($_ -match "T-\d+") { $matches[0] }
    } | Select-Object -Unique

    $taskList = if ($taskIds) { $taskIds -join ", " } else { "unknown task" }

    Write-Output ""
    Write-Output "[COMPLETION CHECK] Task(s) marked ✅ DONE: $taskList"
    Write-Output ""
    Write-Output "@techLead — verify ALL Definition of Done criteria before closing:"
    Write-Output ""
    Write-Output "  DESIGN PHASE"
    Write-Output "  [ ] observability_design.md complete (CloudWatch alarms, structured log schema, X-Ray)"
    Write-Output "  [ ] reliability_design.md complete (RTO/RPO defined, failure modes documented, DLQ config)"
    Write-Output "  [ ] generate_cdk_boilerplate.md complete (tagged, private subnets, IAM scoped)"
    Write-Output "  [ ] security_group_audit.md cleared (no FAIL verdicts)"
    Write-Output "  [ ] cost_estimation.md complete (Dev vs Prod sizing documented in ADR)"
    Write-Output ""
    Write-Output "  IMPLEMENTATION PHASE"
    Write-Output "  [ ] implement_logic.md complete (TypeScript strict, ≤30 lines/fn, custom errors)"
    Write-Output "  [ ] resilience_patterns.md complete (retry backoff, idempotency, DLQ wiring, timeouts)"
    Write-Output "  [ ] add_dependencies.md audit clean (no critical CVEs, licenses approved)"
    Write-Output ""
    Write-Output "  REVIEW PHASE"
    Write-Output "  [ ] complexity_check.md passed (no functions >30 lines, nesting ≤3)"
    Write-Output "  [ ] naming_audit.md passed (no violations)"
    Write-Output "  [ ] dependency_audit.md passed (no new CVEs, no GPL drift)"
    Write-Output "  [ ] documentation_check.md passed (README, .env.example, no TODO/FIXME)"
    Write-Output ""
    Write-Output "  QUALITY PHASE"
    Write-Output "  [ ] write_unit_tests.md complete (≥80% estimated branch coverage)"
    Write-Output "  [ ] mock_aws_responses.md complete (__mocks__/aws.ts barrel exists)"
    Write-Output "  [ ] integration_test.md complete (happy path + DLQ + idempotency tested)"
    Write-Output "  [ ] load_test.md passed (P99 < 1000ms, error rate < 0.1%, DLQ depth = 0)"
    Write-Output "  [ ] penetration_scan.md cleared (no SECURITY FAIL)"
    Write-Output ""
    Write-Output "  DEPLOYMENT PHASE"
    Write-Output "  [ ] pipeline_setup.md complete (CI/CD with OIDC, no long-lived keys)"
    Write-Output "  [ ] environment_promotion.md complete (dev → staging → prod gates defined)"
    Write-Output "  [ ] deployment_verification.md passed (alarms green, DLQ=0, error rate held)"
    Write-Output ""
    Write-Output "  STANDARDS"
    Write-Output "  [ ] .github/shared/standards.md §1-5 compliance confirmed"
    Write-Output "  [ ] AWS Well-Architected: all 6 pillars addressed"
    Write-Output ""
    Write-Output "Run AUDIT_RESULT to confirm. Only then present to user."

    exit 0

} catch {
    Write-Host "[HOOK WARNING] on_task_complete.ps1 encountered an error: $($_.Exception.Message)"
    exit 1
}
