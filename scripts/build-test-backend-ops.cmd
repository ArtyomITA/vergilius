@echo off
REM Costruisce test-backend-ops per verificare che la patch non alteri i risultati
REM degli operatori ggml (richiesto dal CONTRIBUTING quando si tocca il sorgente ggml).
setlocal
set SRC=d:\assistenteeee\llama.cpp-b10549-pre5
set BUILD=%SRC%\build-tests
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set NINJA="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
set VCVARS="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
set CUDA=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4
call %VCVARS% x64 -vcvars_ver=14.38 >nul
set "PATH=%CUDA%\bin;%PATH%"
%CMAKE% -S "%SRC%" -B "%BUILD%" -G Ninja -DCMAKE_MAKE_PROGRAM=%NINJA% ^
  -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DGGML_BACKEND_DL=OFF -DGGML_NATIVE=OFF ^
  -DCMAKE_CUDA_ARCHITECTURES=61-real -DGGML_CUDA_GRAPHS=ON ^
  -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=OFF ^
  -DLLAMA_BUILD_SERVER=OFF -DCUDAToolkit_ROOT="%CUDA%"
if errorlevel 1 (echo ERRORE configure & exit /b 2)
%CMAKE% --build "%BUILD%" --target test-backend-ops
if errorlevel 1 (echo ERRORE build & exit /b 3)
dir /b /s "%BUILD%\*test-backend-ops*.exe"
endlocal
