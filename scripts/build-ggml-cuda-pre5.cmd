@echo off
REM Build isolata di ggml-cuda.dll per sm_61 (GTX 1080) — onda 5.
REM
REM Perche' Ninja e non MSBuild: l'integrazione CUDA in Visual Studio richiede i file
REM BuildCustomizations (CUDA 12.4.props) che l'installer non registra sempre; MSBuild
REM fallisce con CudaToolkitDir vuoto o FileTracker E_ACCESSDENIED. Ninja chiama nvcc
REM direttamente dentro l'ambiente vcvars e salta tutto quel percorso.
REM
REM Perche' il toolset 14.38 e non 14.44: CUDA 12.4 supporta MSVC fino a 193x; il
REM workload "latest" installa 14.44 (1944), che nvcc RIFIUTA. 14.38 = 1938, supportato.
REM
REM Uso:  scripts\build-ggml-cuda-pre5.cmd  [configure|build|all]
REM Esito: build-pre5\bin\ggml-cuda.dll  (NON viene copiata in produzione)

setlocal
set SRC=d:\assistenteeee\llama.cpp-b10549-pre5
REM build-ninja, NON build-pre5: quest'ultima ha una CMakeCache di Visual Studio
REM (tentativo MSBuild dell'altro agente) e i generatori non si mescolano.
set BUILD=%SRC%\build-ninja
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set NINJA="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
set VCVARS="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
set CUDA=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4

if "%~1"=="" (set AZIONE=all) else (set AZIONE=%~1)

call %VCVARS% x64 -vcvars_ver=14.38 >nul
if errorlevel 1 (echo ERRORE: vcvars 14.38 non disponibile & exit /b 1)

set "PATH=%CUDA%\bin;%PATH%"
where cl.exe >nul 2>&1  || (echo ERRORE: cl.exe non nel PATH & exit /b 1)
where nvcc.exe >nul 2>&1 || (echo ERRORE: nvcc.exe non nel PATH & exit /b 1)

echo === compilatori ===
cl 2>&1 | findstr /C:"Version"
nvcc --version | findstr /C:"release"

if "%AZIONE%"=="build" goto :build

echo.
echo === configure (Ninja, sm_61, solo backend CUDA dinamico) ===
%CMAKE% -S "%SRC%" -B "%BUILD%" -G Ninja ^
  -DCMAKE_MAKE_PROGRAM=%NINJA% ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DGGML_CUDA=ON ^
  -DGGML_BACKEND_DL=ON ^
  -DGGML_CPU=OFF ^
  -DGGML_NATIVE=OFF ^
  -DCMAKE_CUDA_ARCHITECTURES=61-real ^
  -DGGML_CUDA_GRAPHS=ON ^
  -DLLAMA_BUILD_TESTS=OFF ^
  -DLLAMA_BUILD_EXAMPLES=OFF ^
  -DLLAMA_BUILD_TOOLS=OFF ^
  -DLLAMA_BUILD_SERVER=OFF ^
  -DCUDAToolkit_ROOT="%CUDA%"
if errorlevel 1 (echo ERRORE: configure fallita & exit /b 2)
if "%AZIONE%"=="configure" goto :fine

:build
echo.
echo === build target ggml-cuda ===
%CMAKE% --build "%BUILD%" --target ggml-cuda
if errorlevel 1 (echo ERRORE: build fallita & exit /b 3)

echo.
echo === artefatto ===
dir /b /s "%BUILD%\*ggml-cuda*.dll"

:fine
echo.
echo FATTO (%AZIONE%). La DLL NON e' stata copiata in produzione.
endlocal
