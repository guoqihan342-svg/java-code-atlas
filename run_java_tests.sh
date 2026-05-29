#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZER_DIR="$ROOT_DIR/java-analyzer"
LIB_DIR="$ANALYZER_DIR/target/test-lib"
MAIN_CLASSES="$ANALYZER_DIR/target/classes"
TEST_CLASSES="$ANALYZER_DIR/target/test-classes"

mkdir -p "$LIB_DIR" "$MAIN_CLASSES" "$TEST_CLASSES"

download_if_missing() {
  local url="$1"
  local dest="$2"
  if [[ ! -f "$dest" ]]; then
    curl -fsSL "$url" -o "$dest"
  fi
}

download_if_missing "https://repo.maven.apache.org/maven2/org/junit/jupiter/junit-jupiter-api/5.10.0/junit-jupiter-api-5.10.0.jar" "$LIB_DIR/junit-jupiter-api-5.10.0.jar"
download_if_missing "https://repo.maven.apache.org/maven2/org/junit/jupiter/junit-jupiter-engine/5.10.0/junit-jupiter-engine-5.10.0.jar" "$LIB_DIR/junit-jupiter-engine-5.10.0.jar"
download_if_missing "https://repo.maven.apache.org/maven2/org/junit/platform/junit-platform-console-standalone/1.10.0/junit-platform-console-standalone-1.10.0.jar" "$LIB_DIR/junit-platform-console-standalone-1.10.0.jar"

M2_CP="$(find "$HOME/.m2/repository" "$LIB_DIR" -name '*.jar' -print | tr '\n' ':')"
MAIN_CP="$M2_CP"
TEST_CP="$MAIN_CLASSES:$M2_CP"

find "$ANALYZER_DIR/src/main/java" -name '*.java' -print > "$ANALYZER_DIR/target/main-sources.txt"
find "$ANALYZER_DIR/src/test/java" -name '*.java' -print > "$ANALYZER_DIR/target/test-sources.txt"

javac -cp "$MAIN_CP" -d "$MAIN_CLASSES" @"$ANALYZER_DIR/target/main-sources.txt"
javac -cp "$TEST_CP" -d "$TEST_CLASSES" @"$ANALYZER_DIR/target/test-sources.txt"

java -jar "$LIB_DIR/junit-platform-console-standalone-1.10.0.jar" \
  --class-path "$MAIN_CLASSES:$TEST_CLASSES:$M2_CP" \
  --scan-class-path "$TEST_CLASSES" \
  --include-classname '^io\.github\.javacodeatlas\..*Test$' \
  --exclude-engine junit-vintage
