param(
    [string]$ProjectRoot = "C:\Users\len\Documents\Daily Research",
    [string]$Config = "config.example.json",
    [int]$Days = 14
)

Set-Location -LiteralPath $ProjectRoot
python -m daily_research_agent --config $Config --days $Days

