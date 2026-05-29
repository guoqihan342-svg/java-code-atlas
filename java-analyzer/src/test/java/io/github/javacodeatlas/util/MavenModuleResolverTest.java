package io.github.javacodeatlas.util;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class MavenModuleResolverTest {
    @TempDir
    Path tempDir;

    @Test
    void resolveSingleModuleProject() throws IOException {
        writePom(tempDir, """
            <project>
              <modelVersion>4.0.0</modelVersion>
              <groupId>com.example</groupId>
              <artifactId>single</artifactId>
            </project>
            """);
        Files.createDirectories(tempDir.resolve("src/main/java"));

        List<MavenModuleResolver.ModuleInfo> modules = MavenModuleResolver.resolve(tempDir);

        assertEquals(1, modules.size());
        MavenModuleResolver.ModuleInfo module = modules.get(0);
        assertEquals(tempDir.getFileName().toString(), module.artifactId());
        assertEquals("jar", module.packaging());
        assertEquals(tempDir, module.moduleRoot());
        assertEquals(tempDir.resolve("src/main/java"), module.sourceRoot());
    }

    @Test
    void resolveMultiModuleAggregator() throws IOException {
        writePom(tempDir, """
            <project>
              <packaging>pom</packaging>
              <modules>
                <module>sub1</module>
                <module>sub2</module>
              </modules>
            </project>
            """);
        moduleWithPom("sub1", "<project><artifactId>sub1</artifactId><packaging>jar</packaging></project>");
        moduleWithPom("sub2", "<project><artifactId>sub2</artifactId></project>");

        List<MavenModuleResolver.ModuleInfo> modules = MavenModuleResolver.resolve(tempDir);

        assertEquals(2, modules.size());
        assertEquals(List.of("sub1", "sub2"), modules.stream().map(MavenModuleResolver.ModuleInfo::artifactId).toList());
        assertEquals(List.of("jar", "jar"), modules.stream().map(MavenModuleResolver.ModuleInfo::packaging).toList());
    }

    @Test
    void resolveNestedAggregatorIncludesRealNestedModule() throws IOException {
        writePom(tempDir, """
            <project>
              <packaging>pom</packaging>
              <modules><module>platform</module></modules>
            </project>
            """);
        writePom(tempDir.resolve("platform"), """
            <project>
              <packaging>pom</packaging>
              <modules><module>service-api</module></modules>
            </project>
            """);
        moduleWithPom("platform/service-api", """
            <project>
              <artifactId>service-api</artifactId>
              <packaging>jar</packaging>
            </project>
            """);

        List<MavenModuleResolver.ModuleInfo> modules = MavenModuleResolver.resolve(tempDir);

        assertEquals(1, modules.size());
        assertEquals("service-api", modules.get(0).artifactId());
        assertEquals(tempDir.resolve("platform/service-api/src/main/java"), modules.get(0).sourceRoot());
    }

    @Test
    void parsePackagingReadsJar() throws IOException {
        Path pom = writePom(tempDir, "<project><packaging>jar</packaging></project>");

        assertEquals("jar", MavenModuleResolver.parsePackaging(pom));
    }

    @Test
    void parsePackagingReadsPomWithoutOffsetRegression() throws IOException {
        Path pom = writePom(tempDir, "<project><packaging>pom</packaging></project>");

        assertEquals("pom", MavenModuleResolver.parsePackaging(pom));
    }

    @Test
    void parsePackagingDefaultsToJarWhenMissing() throws IOException {
        Path pom = writePom(tempDir, "<project><artifactId>demo</artifactId></project>");

        assertEquals("jar", MavenModuleResolver.parsePackaging(pom));
    }

    @Test
    void parseArtifactIdAndGroupId() throws IOException {
        Path pom = writePom(tempDir, """
            <project>
              <groupId>io.github.example</groupId>
              <artifactId>sample-app</artifactId>
            </project>
            """);

        assertEquals("sample-app", MavenModuleResolver.parseArtifactId(pom, "fallback-artifact"));
        assertEquals("io.github.example", MavenModuleResolver.parseGroupId(pom, "fallback-group"));
    }

    @Test
    void malformedXmlReturnsFallbacks() throws IOException {
        Path pom = writePom(tempDir, """
            <project>
              <groupId>com.example
              <artifactId>broken
              <packaging>pom
            """);

        assertEquals("jar", MavenModuleResolver.parsePackaging(pom));
        assertEquals("fallback-artifact", MavenModuleResolver.parseArtifactId(pom, "fallback-artifact"));
        assertEquals("fallback-group", MavenModuleResolver.parseGroupId(pom, "fallback-group"));
    }

    private Path moduleWithPom(String modulePath, String pomXml) throws IOException {
        Path module = tempDir.resolve(modulePath);
        Files.createDirectories(module.resolve("src/main/java"));
        return writePom(module, pomXml);
    }

    private static Path writePom(Path root, String content) throws IOException {
        Files.createDirectories(root);
        Path pom = root.resolve("pom.xml");
        Files.writeString(pom, content);
        assertTrue(Files.exists(pom));
        return pom;
    }
}
