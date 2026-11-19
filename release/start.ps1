# Start EPM2Mod (Windows). Everything it downloads stays in this folder (.uv): delete the folder to remove it.
#   start.ps1           open the installer page in the browser
#   start.ps1 install --card E:\   write EPM2Mod to the SD card on the command line
#   start.ps1 --help    the other commands for camera owners
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 may offer only old TLS versions, which GitHub refuses
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
Set-Location -LiteralPath $PSScriptRoot

# uv, pinned: version and the sha256 of each download (https://github.com/astral-sh/uv/releases/tag/0.13.6)
$UvVersion = '0.13.6'
$Assets = @{
  'AMD64' = @('uv-x86_64-pc-windows-msvc', 'a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f')
  'ARM64' = @('uv-aarch64-pc-windows-msvc', 'c2426c0c8e28b53d8c440e47a18d96ad4db51e159866c0e81435b196d7f0081c')
}
$Machine = $env:PROCESSOR_ARCHITEW6432
if (-not $Machine) { $Machine = $env:PROCESSOR_ARCHITECTURE }
if (-not $Assets.ContainsKey($Machine)) { throw "This start script works on 64-bit Windows (x64 or ARM). This computer is $Machine." }
$Asset, $Sha = $Assets[$Machine]

$Bin = Join-Path $PSScriptRoot '.uv\bin'
$Uv = Join-Path $Bin 'uv.exe'
$Have = if (Test-Path -LiteralPath $Uv) { ((& $Uv --version) -split ' ')[1] } else { '' }
if ($Have -ne $UvVersion) {
  [Console]::Error.WriteLine("Downloading uv $UvVersion.")
  New-Item -ItemType Directory -Force -Path $Bin | Out-Null
  $Archive = Join-Path $PSScriptRoot ".uv\$Asset.zip"
  (New-Object System.Net.WebClient).DownloadFile("https://github.com/astral-sh/uv/releases/download/$UvVersion/$Asset.zip", $Archive)
  # .NET for the checksum and the unzip: they work in every PowerShell, whatever its module path
  $Hasher = [System.Security.Cryptography.SHA256]::Create()
  $Stream = [System.IO.File]::OpenRead($Archive)
  try { $Got = -join ($Hasher.ComputeHash($Stream) | ForEach-Object { $_.ToString('x2') }) } finally { $Stream.Dispose() }
  if ($Got -ne $Sha) {
    Remove-Item -LiteralPath $Archive
    throw 'The uv download has the wrong checksum. Nothing was installed. Try again later.'
  }
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  Get-ChildItem -LiteralPath $Bin -Filter 'uv*.exe' | Remove-Item
  [System.IO.Compression.ZipFile]::ExtractToDirectory($Archive, $Bin)
  Remove-Item -LiteralPath $Archive
}

# Python 3.12 from uv, kept in this folder; the package needs nothing else (standard library only).
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.uv\cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.uv\python'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'cli/src'
# the name in usage lines, examples and hints: the one a user types here
$env:EPM2MOD_PROG = '.\start.ps1'
# @(...) keeps one argument a list: a lone string would be passed letter by letter
$Command = @(if ($args.Count -eq 0) { 'serve' } else { $args })
& $Uv run --no-project --managed-python --python 3.12 python -m epm2mod @Command
exit $LASTEXITCODE
