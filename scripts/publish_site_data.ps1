param(
    [string]$ProjectRoot = "C:\Users\len\Documents\Daily Research",
    [string]$Message = "Update site data from Codex weekly report"
)

$git = "C:\Users\len\AppData\Local\GitHubDesktop\app-3.6.3\resources\app\git\cmd\git.exe"

Set-Location -LiteralPath $ProjectRoot

& $git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    throw "git pull --rebase failed. Resolve conflicts before publishing."
}

& $git add site/data/papers.json outputs/weekly_reports docs/consensus_quota_policy.md prompts/weekly_consensus_report.md consensus_usage.example.json config.weekly.json

$status = & $git status --porcelain
if (-not $status) {
    Write-Output "No site data changes to publish."
    exit 0
}

& $git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    throw "git commit failed."
}

& $git push
if ($LASTEXITCODE -ne 0) {
    throw "git push failed."
}

Write-Output "Published site data to GitHub."

