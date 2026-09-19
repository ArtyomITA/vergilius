[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Source = 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\extras\visual_studio_integration\MSBuildExtensions'
$Destination = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Microsoft\VC\v170\BuildCustomizations'
$Names = @(
    'CUDA 12.4.props',
    'CUDA 12.4.targets',
    'CUDA 12.4.xml',
    'Nvda.Build.CudaTasks.v12.4.dll'
)

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "CUDA integration source missing: $Source"
}
$Null = New-Item -ItemType Directory -Path $Destination -Force
foreach ($Name in $Names) {
    $InputPath = Join-Path $Source $Name
    if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
        throw "Missing official integration file: $InputPath"
    }
    Copy-Item -LiteralPath $InputPath -Destination (Join-Path $Destination $Name) -Force
}

foreach ($Name in $Names) {
    $InputHash = (Get-FileHash -LiteralPath (Join-Path $Source $Name) -Algorithm SHA256).Hash
    $OutputHash = (Get-FileHash -LiteralPath (Join-Path $Destination $Name) -Algorithm SHA256).Hash
    if ($InputHash -ne $OutputHash) { throw "Hash mismatch: $Name" }
    Write-Output "$Name $OutputHash"
}
