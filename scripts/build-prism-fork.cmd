@echo off
REM Build del fork PrismML-Eng/llama.cpp (Ternary Bonsai, tipi PTQ1_0/PQ2_0) per sm_61.
REM Stessa ricetta dell'onda 5: Ninja + vcvars 14.38 + CUDA 12.4. Sorgente su C: (D: ha NTFS corrotto).
REM Esito: C:\vergilius-build\prism-llama\build-ninja\bin\llama-server.exe / llama-bench.exe / llama-cli.exe
setlocal
set SRC=C:\vergilius-build\prism-llama
set BUILD=%SRC%\build-ninja
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set NINJA="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
set VCVARS="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
set CUDA=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4

call %VCVARS% x64 -vcvars_ver=14.38 >nul
if errorlevel 1 (echo ERRORE: vcvars 14.38 non disponibile & exit /b 1)
set "PATH=%CUDA%\bin;%PATH%"

echo === configure ===
%CMAKE% -S "%SRC%" -B "%BUILD%" -G Ninja ^
  -DCMAKE_MAKE_PROGRAM=%NINJA% ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DGGML_CUDA=ON ^
  -DGGML_NATIVE=OFF ^
  -DGGML_AVX2=ON ^
  -DCMAKE_CUDA_ARCHITECTURES=61-real ^
  -DGGML_CUDA_GRAPHS=ON ^
  -DLLAMA_CURL=OFF ^
  -DLLAMA_BUILD_TESTS=OFF ^
  -DLLAMA_BUILD_EXAMPLES=OFF ^
  -DCMAKE_CUDA_HOST_COMPILER="C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.38.33130/bin/Hostx64/x64/cl.exe" ^
  -DCUDAToolkit_ROOT="%CUDA%"
if errorlevel 1 (echo ERRORE: configure fallita & exit /b 2)

echo === build ===
%CMAKE% --build "%BUILD%" --target llama-server llama-bench llama-cli -j 8
if errorlevel 1 (echo ERRORE: build fallita & exit /b 3)

echo === artefatti ===
dir /b "%BUILD%\bin\llama-server.exe" "%BUILD%\bin\llama-bench.exe" "%BUILD%\bin\llama-cli.exe"
echo FATTO
endlocal
