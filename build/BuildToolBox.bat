@echo off
REM === Clean previous build and dist folders ===
REM Navigate to parent directory
cd /d "%~dp0.."

if exist build\build (
    echo Removing old build\build folder...
    rmdir /s /q build\build
)
if exist dist (
    echo Removing old dist folder...
    rmdir /s /q dist
)

REM === Path to PyInstaller inside .venv ===
set PYI=%~dp0..\.venv\Scripts\pyinstaller.exe

REM === Run PyInstaller with spec file (ONEFILE is configured in spec, not via CLI flag) ===
echo Running PyInstaller...
"%PYI%" --noconfirm build\BuildToolBox.spec

REM === Target folder ===
set DIST_DIR=%~dp0..\dist\AdminToolBox

echo Preparing dist\AdminToolBox...
if not exist "%DIST_DIR%" (
    mkdir "%DIST_DIR%"
)

REM === Move main.exe and _internal into AdminToolBox (if present) ===
echo Moving main.exe and _internal into dist\AdminToolBox...

if exist dist\main.exe (
    move /Y "dist\main.exe" "%DIST_DIR%\main.exe" >nul
)

if exist dist\_internal (
    if exist "%DIST_DIR%\_internal" (
        rmdir /s /q "%DIST_DIR%\_internal"
    )
    move "dist\_internal" "%DIST_DIR%\" >nul
)

REM === Always create UserList folder ===
echo Creating UserList folder in dist...
mkdir "%DIST_DIR%\UserList" >nul 2>&1
copy /Y "%~dp0..\UserList\readme.txt" "%DIST_DIR%\UserList\"

REM === Always create Services folder ===
echo Creating Services folder in dist...
mkdir "%DIST_DIR%\Services" >nul 2>&1

REM === Always create Policies folder (without LGPO.exe) ===
echo Creating Policies folder in dist...
mkdir "%DIST_DIR%\Policies" >nul 2>&1

REM === Place LGPO.exe next to main.exe ===
echo Copying LGPO.exe next to main.exe...
copy /Y "%~dp0..\Policies\LGPO.exe" "%DIST_DIR%\LGPO.exe"

REM === Always create USB folder ===
echo Creating USB folder in dist...
mkdir "%DIST_DIR%\USB" >nul 2>&1

REM === Always create ProgramList folder ===
echo Creating ProgramList folder in dist...
mkdir "%DIST_DIR%\ProgramList" >nul 2>&1
copy /Y "%~dp0..\ProgramList\restricted_programs.txt" "%DIST_DIR%\ProgramList\"

echo.
echo === Build finished successfully ===
pause
