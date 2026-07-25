param(
    [string]$ProjectRoot = "C:\Users\len\Documents\Daily Research",
    [string]$Config = "config.weekly.json",
    [int]$Days = 4
)

Set-Location -LiteralPath $ProjectRoot
python -m daily_research_agent --config $Config --days $Days
