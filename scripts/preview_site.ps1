param(
    [string]$ProjectRoot = "C:\Users\len\Documents\Daily Research",
    [int]$Port = 8000
)

Set-Location -LiteralPath $ProjectRoot
python -m http.server $Port -d site

