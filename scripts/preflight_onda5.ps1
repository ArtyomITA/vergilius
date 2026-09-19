<#
.SYNOPSIS
Pre-Wave-5 reproducible build gate for the isolated llama.cpp b10549 worktree.

.DESCRIPTION
No production DLL is overwritten. Default mode only inspects source/toolchain.
Use -Configure after CUDA 12.4 + MSVC + CMake are present, then -Build to build
only ggml-cuda in the isolated worktree.
#>

[CmdletBinding()]
param(
    [switch]$Configure,
    [switch]$Build,
    [string]$Source = 'D:\assistenteeee\llama.cpp-b10549-pre5',
    [string]$BuildDirectory = 'D:\assistenteeee\llama.cpp-b10549-pre5\build-pre5',
    [string]$ResultsDirectory = 'D:\assistenteeee\ricerche\opt-1080\misure\pre5'
)

$ErrorActionPreference = 'Stop'
$ExpectedCommit = 'b2e5e9b28'

function Find-Executable {
    param([string]$Name, [string[]]$Candidates)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }
    return $null
}

function Invoke-CapturedVersion {
    param([string]$Executable, [string[]]$Arguments)
    if (-not $Executable) { return $null }
    try {
        return ((& $Executable @Arguments 2>&1) | Select-Object -First 4) -join "`n"
    } catch {
        return "ERROR: $($_.Exception.Message)"
    }
}

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Missing isolated source worktree: $Source"
}

$Git = Find-Executable 'git.exe' @('C:\Program Files\Git\cmd\git.exe')
if (-not $Git) { throw 'git.exe not found' }
$CMake = Find-Executable 'cmake.exe' @('C:\Program Files\CMake\bin\cmake.exe')
$Ninja = Find-Executable 'ninja.exe' @('C:\Program Files\Ninja\ninja.exe')
$Nvcc = Find-Executable 'nvcc.exe' @('C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\nvcc.exe')
$VsWhere = Find-Executable 'vswhere.exe' @(
    'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe',
    'C:\Program Files\Microsoft Visual Studio\Installer\vswhere.exe'
)

$GitSafety = "safe.directory=$($Source -replace '\\','/')"
$Head = (& $Git -c $GitSafety -c core.filemode=false -C $Source rev-parse HEAD).Trim()
# The parent repository was created with core.filemode=true. Windows cannot
# preserve POSIX executable bits, which creates 123 false modifications in a
# brand-new worktree. Ignore file mode only; content changes still fail closed.
$Status = (& $Git -c $GitSafety -c core.filemode=false -C $Source status --porcelain=v1) -join "`n"
$CommitOk = $Head.StartsWith($ExpectedCommit)
$Clean = [string]::IsNullOrWhiteSpace($Status)
if (-not $CommitOk) { throw "Wrong source commit: $Head (expected $ExpectedCommit...)" }
if (-not $Clean) { throw "Isolated source is dirty; refusing pre-5 build:`n$Status" }

$VsInstall = $null
if ($VsWhere) {
    $VsInstall = ((& $VsWhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath) | Select-Object -First 1)
}
$Msvc1438 = $null
if ($VsInstall) {
    $Msvc1438 = Get-ChildItem -LiteralPath (Join-Path $VsInstall 'VC\Tools\MSVC') -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like '14.38.*' } |
        Sort-Object Name -Descending |
        Select-Object -First 1
}
$CudaVersion = Invoke-CapturedVersion $Nvcc @('--version')
$Cuda124 = $Nvcc -and ($CudaVersion -match 'release 12\.4')
$CudaRoot = if ($Nvcc) { Split-Path (Split-Path $Nvcc -Parent) -Parent } else { $null }
$ToolchainReady = [bool]($CMake -and $Nvcc -and $VsInstall -and $Msvc1438 -and $Cuda124)

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Null = New-Item -ItemType Directory -Path $ResultsDirectory -Force
$ManifestPath = Join-Path $ResultsDirectory "pre5-$Stamp.json"

$Manifest = [ordered]@{
    schema = 'odysseus.pre5-build-gate.v1'
    created_at = (Get-Date).ToString('o')
    source = $Source
    build_directory = $BuildDirectory
    expected_commit = $ExpectedCommit
    head = $Head
    source_clean = $Clean
    production_reference = 'D:\assistenteeee\llama-cuda124-new'
    production_overwritten = $false
    tools = [ordered]@{
        git = $Git
        cmake = $CMake
        cmake_version = Invoke-CapturedVersion $CMake @('--version')
        ninja = $Ninja
        ninja_version = Invoke-CapturedVersion $Ninja @('--version')
        nvcc = $Nvcc
        nvcc_version = $CudaVersion
        cuda_root = $CudaRoot
        cuda_12_4 = [bool]$Cuda124
        vswhere = $VsWhere
        visual_studio = $VsInstall
        msvc_14_38 = if ($Msvc1438) { $Msvc1438.FullName } else { $null }
        ready = $ToolchainReady
    }
    configure_requested = [bool]$Configure
    build_requested = [bool]$Build
    configure_exit_code = $null
    build_exit_code = $null
    output_dll = $null
    output_dll_sha256 = $null
}

try {
    if ($Configure -or $Build) {
        if (-not $ToolchainReady) {
            throw 'Toolchain incomplete: need CUDA Toolkit 12.4, MSVC 14.38 C++ Build Tools, and CMake.'
        }
        $Null = New-Item -ItemType Directory -Path $BuildDirectory -Force
        $ConfigureArgs = @(
            '--fresh',
            '-S', $Source,
            '-B', $BuildDirectory,
            '-G', 'Visual Studio 17 2022',
            '-A', 'x64',
            '-T', 'v143,version=14.38,cuda=12.4',
            '-DGGML_CUDA=ON',
            '-DGGML_BACKEND_DL=ON',
            '-DGGML_CPU=OFF',
            '-DGGML_NATIVE=OFF',
            "-DCUDAToolkit_ROOT=$CudaRoot",
            "-DCMAKE_CUDA_COMPILER=$Nvcc",
            # CMake finds nvcc through CUDAToolkit_ROOT, but the VS CUDA .targets
            # independently consumes the MSBuild CudaToolkitDir property.
            # Fresh shells opened before the Toolkit install do not inherit
            # CUDA_PATH, so make both discovery paths explicit and reproducible.
            "-DCMAKE_VS_GLOBALS=CudaToolkitDir=$CudaRoot\\",
            '-DCMAKE_CUDA_ARCHITECTURES=61-real',
            '-DGGML_CUDA_GRAPHS=ON'
        )
        Write-Host "configure: $CMake $($ConfigureArgs -join ' ')"
        $PriorGitConfigCount = $env:GIT_CONFIG_COUNT
        $PriorGitConfigKey = $env:GIT_CONFIG_KEY_0
        $PriorGitConfigValue = $env:GIT_CONFIG_VALUE_0
        $PriorCudaPath = $env:CUDA_PATH
        $PriorCudaPath124 = $env:CUDA_PATH_V12_4
        try {
            $env:GIT_CONFIG_COUNT = '1'
            $env:GIT_CONFIG_KEY_0 = 'safe.directory'
            $env:GIT_CONFIG_VALUE_0 = ($Source -replace '\\','/')
            $env:CUDA_PATH = $CudaRoot
            $env:CUDA_PATH_V12_4 = $CudaRoot
            & $CMake @ConfigureArgs
        } finally {
            $env:GIT_CONFIG_COUNT = $PriorGitConfigCount
            $env:GIT_CONFIG_KEY_0 = $PriorGitConfigKey
            $env:GIT_CONFIG_VALUE_0 = $PriorGitConfigValue
            $env:CUDA_PATH = $PriorCudaPath
            $env:CUDA_PATH_V12_4 = $PriorCudaPath124
        }
        $Manifest.configure_exit_code = $LASTEXITCODE
        if ($LASTEXITCODE -ne 0) { throw "CMake configure failed: $LASTEXITCODE" }
    }

    if ($Build) {
        $BuildArgs = @('--build', $BuildDirectory, '--config', 'Release', '--target', 'ggml-cuda')
        Write-Host "build: $CMake $($BuildArgs -join ' ')"
        & $CMake @BuildArgs
        $Manifest.build_exit_code = $LASTEXITCODE
        if ($LASTEXITCODE -ne 0) { throw "ggml-cuda build failed: $LASTEXITCODE" }
        $Dll = Get-ChildItem -LiteralPath $BuildDirectory -Recurse -Filter 'ggml-cuda.dll' -File |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 1
        if (-not $Dll) { throw 'Build succeeded but ggml-cuda.dll was not found' }
        $Manifest.output_dll = $Dll.FullName
        $Manifest.output_dll_sha256 = (Get-FileHash -LiteralPath $Dll.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
} catch {
    $Manifest.error = "$($_.Exception.GetType().Name): $($_.Exception.Message)"
    throw
} finally {
    $Json = $Manifest | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($ManifestPath, $Json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "manifest: $ManifestPath"
}

if (-not $ToolchainReady) {
    Write-Host 'PRE5: SOURCE READY; TOOLCHAIN MISSING'
    exit 2
}
if ($Build) {
    Write-Host "PRE5: PRISTINE CUDA DLL BUILT -> $($Manifest.output_dll)"
} elseif ($Configure) {
    Write-Host 'PRE5: PRISTINE CUDA BUILD CONFIGURED'
} else {
    Write-Host 'PRE5: SOURCE + TOOLCHAIN READY'
}
