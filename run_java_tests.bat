@echo off
setlocal enabledelayedexpansion

REM run_java_tests.bat — Windows batch equivalent of run_java_tests.ps1
REM Usage: run_java_tests.bat
REM Prerequisites: JDK 17+

set ROOT_DIR=%~dp0
set ANALYZER_DIR=%ROOT_DIR%java-analyzer
set LIB_DIR=%ANALYZER_DIR%\target\test-lib
set MAIN_CLASSES=%ANALYZER_DIR%\target\classes
set TEST_CLASSES=%ANALYZER_DIR%\target\test-classes

if not exist "%LIB_DIR%" mkdir "%LIB_DIR%"
if not exist "%MAIN_CLASSES%" mkdir "%MAIN_CLASSES%"
if not exist "%TEST_CLASSES%" mkdir "%TEST_CLASSES%"

REM Download JARs if missing
if not exist "%LIB_DIR%\junit-jupiter-api-5.10.0.jar" (
    echo Downloading JUnit JARs...
    powershell -Command "Invoke-WebRequest -Uri 'https://repo.maven.apache.org/maven2/org/junit/jupiter/junit-jupiter-api/5.10.0/junit-jupiter-api-5.10.0.jar' -OutFile '%LIB_DIR%\junit-jupiter-api-5.10.0.jar'"
    powershell -Command "Invoke-WebRequest -Uri 'https://repo.maven.apache.org/maven2/org/junit/jupiter/junit-jupiter-engine/5.10.0/junit-jupiter-engine-5.10.0.jar' -OutFile '%LIB_DIR%\junit-jupiter-engine-5.10.0.jar'"
    powershell -Command "Invoke-WebRequest -Uri 'https://repo.maven.apache.org/maven2/org/junit/platform/junit-platform-console-standalone/1.10.0/junit-platform-console-standalone-1.10.0.jar' -OutFile '%LIB_DIR%\junit-platform-console-standalone-1.10.0.jar'"
)

set M2_REPO=%USERPROFILE%\.m2\repository
set CP=%LIB_DIR%\junit-jupiter-api-5.10.0.jar;%LIB_DIR%\junit-jupiter-engine-5.10.0.jar;%LIB_DIR%\junit-platform-console-standalone-1.10.0.jar

if exist "%M2_REPO%" (
    for /r "%M2_REPO%" %%i in (*.jar) do if exist "%%i" set CP=!CP!;%%i
)

REM Compile main sources
echo Compiling main sources...
set MAIN_FILES=
for /r "%ANALYZER_DIR%\src\main\java" %%i in (*.java) do if exist "%%i" set MAIN_FILES=!MAIN_FILES! "%%i"
javac -cp "%CP%" -d "%MAIN_CLASSES%" !MAIN_FILES!
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

REM Compile test sources
echo Compiling test sources...
set TEST_FILES=
for /r "%ANALYZER_DIR%\src\test\java" %%i in (*.java) do if exist "%%i" set TEST_FILES=!TEST_FILES! "%%i"
set TEST_CP=%MAIN_CLASSES%;%CP%
javac -cp "%TEST_CP%" -d "%TEST_CLASSES%" !TEST_FILES!
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

REM Run tests
echo Running tests...
set RUN_CP=%MAIN_CLASSES%;%TEST_CLASSES%;%CP%
java -jar "%LIB_DIR%\junit-platform-console-standalone-1.10.0.jar" ^
    --class-path "%RUN_CP%" ^
    --scan-class-path "%TEST_CLASSES%" ^
    --include-classname "^io\.github\.javacodeatlas\..*Test$" ^
    --exclude-engine junit-vintage

exit /b %ERRORLEVEL%
