package io.github.jstruct.util;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class JdkVersionDetectorTest {
    @TempDir
    Path tempDir;

    @Test
    void detectFromMavenCompilerRelease() throws IOException {
        write("pom.xml", """
            <project>
              <properties>
                <maven.compiler.release>17</maven.compiler.release>
              </properties>
            </project>
            """);

        assertEquals("17", JdkVersionDetector.detect(tempDir));
    }

    @Test
    void detectFromMavenCompilerSource() throws IOException {
        write("pom.xml", """
            <project>
              <properties>
                <maven.compiler.source>11</maven.compiler.source>
              </properties>
            </project>
            """);

        assertEquals("11", JdkVersionDetector.detect(tempDir));
    }

    @Test
    void detectFromGradleSourceCompatibility() throws IOException {
        write("build.gradle", """
            plugins { id 'java' }
            sourceCompatibility = "1.8"
            """);

        assertEquals("1.8", JdkVersionDetector.detect(tempDir));
    }

    @Test
    void detectFromJavaVersionFile() throws IOException {
        write(".java-version", "21\n");

        assertEquals("21", JdkVersionDetector.detect(tempDir));
    }

    @Test
    void detectFallsBackToSystemJavaVersion() {
        assertEquals(System.getProperty("java.version"), JdkVersionDetector.detect(tempDir));
    }

    @Test
    void detectTrimsWhitespaceAndNewlinesInVersionStrings() throws IOException {
        write("pom.xml", """
            <project>
              <properties>
                <maven.compiler.release>
                  17
                </maven.compiler.release>
              </properties>
            </project>
            """);

        assertEquals("17", JdkVersionDetector.detect(tempDir));
    }

    private void write(String relativePath, String content) throws IOException {
        Path path = tempDir.resolve(relativePath);
        Files.createDirectories(path.getParent() == null ? tempDir : path.getParent());
        Files.writeString(path, content);
    }
}
