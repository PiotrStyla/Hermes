param([string]$Key, [string]$Value, [string]$Path = '.env')
$lines = if (Test-Path $Path) { Get-Content $Path } else { @() }
$found = $false
$out = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($Key))=") {
        $found = $true
        "$Key=$Value"
    } else {
        $line
    }
}
if (-not $found) { $out += "$Key=$Value" }
Set-Content -Path $Path -Value $out -Encoding UTF8
Write-Host "Updated $Key in $Path"
