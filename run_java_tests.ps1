# run_java_tests.ps1 — Windows PowerShell equivalent of run_java_tests.sh
# Usage: .\run_java_tests.ps1
# Prerequisites: JDK 17+, curl (or Invoke-WebRequest fallback)

$ErrorActionPreference = "Stop"

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ANALYZER_DIR = Join-Path $ROOT_DIR "java-analyzer"
$LIB_DIR = Join-Path $ANALYZER_DIR "target\test-lib"
$MAIN_CLASSES = Join-Path $ANALYZER_DIR "target\classes"
$TEST_CLASSES = Join-Path $ANALYZER_DIR "target\test-classes"

New-Item -ItemType Directory -Force -Path $LIB_DIR, $MAIN_CLASSES, $TEST_CLASSES | Out-Null

function Download-IfMissing {
    param($Url, $Dest)
    if (-not (Test-Path $Dest)) {
        Write-Host "Downloading $Url ..."
        try {
            curl.exe -fsSL $Url -o $Dest 2>$null
            if ($LASTEXITCODE -ne 0) {
                Invoke-WebRequest -Uri $Url -OutFile $Dest
            }
        } catch {
            Invoke-WebRequest -Uri $Url -OutFile $Dest
        }
    }
}

Download-IfMissing "https://repo.maven.apache.org/maven2/org/junit/jupiter/junit-jupiter-api/5.10.0/junit-jupiter-api-5.10.0.jar" "$LIB_DIR\junit-jupiter-api-5.10.0.jar"
Download-IfMissing "https://repo.maven.apache.org/maven2/org/junit/jupiter/junit-jupiter-engine/5.10.0/junit-jupiter-engine-5.10.0.jar" "$LIB_DIR\junit-jupiter-engine-5.10.0.jar"
Download-IfMissing "https://repo.maven.apache.org/maven2/org/junit/platform/junit-platform-console-standalone/1.10.0/junit-platform-console-standalone-1.10.0.jar" "$LIB_DIR\junit-platform-console-standalone-1.10.0.jar"

# Build classpath (semicolon-separated for Windows)
$M2_REPO = Join-Path $env:USERPROFILE ".m2\repository"
$JARS = @()
if (Test-Path $LIB_DIR) {
    $JARS += Get-ChildItem -Path $LIB_DIR -Filter "*.jar" | ForEach-Object { $_.FullName }
}
if (Test-Path $M2_REPO) {
    $JARS += Get-ChildItem -Path $M2_REPO -Recurse -Filter "*.jar" | ForEach-Object { $_.FullName }
}
$CP = ($JARS -join ";")

# Compile main sources
$MAIN_SOURCES = Get-ChildItem -Path (Join-Path $ANALYZER_DIR "src\main\java") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName }
Write-Host "Compiling $($MAIN_SOURCES.Count) main sources..."
& javac -cp $CP -d $MAIN_CLASSES $MAIN_SOURCES
if ($LASTEXITCODE -ne 0) { throw "javac main compilation failed" }

# Compile test sources
$TEST_SOURCES = Get-ChildItem -Path (Join-Path $ANALYZER_DIR "src\test\java") -Recurse -Filter "*.java" | ForEach-Object { $_.FullName }
$TEST_CP = "$MAIN_CLASSES;$CP"
Write-Host "Compiling $($TEST_SOURCES.Count) test sources..."
& javac -cp $TEST_CP -d $TEST_CLASSES $TEST_SOURCES
if ($LASTEXITCODE -ne 0) { throw "javac test compilation failed" }

# Run tests
Write-Host "Running tests..."
$RUN_CP = "$MAIN_CLASSES;$TEST_CLASSES;$CP"
& java -jar "$LIB_DIR\junit-platform-console-standalone-1.10.0.jar" `
    --class-path $RUN_CP `
    --scan-class-path $TEST_CLASSES `
    --include-classname '^io\.github\.javacodeatlas\..*Test$' `
    --exclude-engine junit-vintage

exit $LASTEXITCODE
