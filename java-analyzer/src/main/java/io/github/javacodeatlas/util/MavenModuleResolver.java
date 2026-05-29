package io.github.javacodeatlas.util;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class MavenModuleResolver {
    public record ModuleInfo(
        String artifactId,
        String packaging,
        Path moduleRoot,
        Path sourceRoot
    ) {}

    public static List<ModuleInfo> resolve(Path projectRoot) throws IOException {
        Path rootPom = projectRoot.resolve("pom.xml");
        if (!Files.exists(rootPom)) {
            Path src = projectRoot.resolve("src/main/java");
            if (Files.exists(src)) {
                return List.of(new ModuleInfo(projectRoot.getFileName().toString(), "jar", projectRoot, src));
            }
            return List.of();
        }

        List<ModuleInfo> modules = new ArrayList<>();
        List<String> moduleNames = parseModules(rootPom);

        if (moduleNames.isEmpty()) {
            Path src = projectRoot.resolve("src/main/java");
            if (Files.exists(src)) {
                modules.add(new ModuleInfo(projectRoot.getFileName().toString(), "jar", projectRoot, src));
            }
        } else {
            for (String name : moduleNames) {
                Path moduleDir = projectRoot.resolve(name);
                Path modulePom = moduleDir.resolve("pom.xml");
                String packaging = "jar";
                if (Files.exists(modulePom)) {
                    packaging = parsePackaging(modulePom);
                }
                if ("pom".equals(packaging)) {
                    // recursion for nested aggregator modules
                    List<ModuleInfo> nested = resolve(moduleDir);
                    modules.addAll(nested);
                    continue;
                }

                Path src = moduleDir.resolve("src/main/java");
                if (Files.exists(src)) {
                    modules.add(new ModuleInfo(name, packaging, moduleDir, src));
                }
            }
        }
        return modules;
    }

    private static List<String> parseModules(Path pom) throws IOException {
        String content = Files.readString(pom);
        List<String> modules = new ArrayList<>();
        int start = content.indexOf("<modules>");
        if (start < 0) return modules;
        int end = content.indexOf("</modules>", start);
        if (end < 0) return modules;
        String block = content.substring(start, end);
        for (int i = 0; i < block.length(); ) {
            int ms = block.indexOf("<module>", i);
            if (ms < 0) break;
            int me = block.indexOf("</module>", ms);
            if (me < 0) break;
            modules.add(block.substring(ms + 8, me).trim());
            i = me + 9;
        }
        return modules;
    }

    public static String parsePackaging(Path pom) throws IOException {
        String content = Files.readString(pom);
        int start = content.indexOf("<packaging>");
        if (start < 0) return "jar";
        int end = content.indexOf("</packaging>", start);
        if (end < 0) return "jar";
        return content.substring(start + 11, end).trim();
    }

    public static String parseArtifactId(Path pom, String fallback) {
        try {
            return parseTag(Files.readString(pom), "artifactId", fallback);
        } catch (IOException ignored) {
            return fallback;
        }
    }

    public static String parseGroupId(Path pom, String fallback) {
        try {
            return parseTag(Files.readString(pom), "groupId", fallback);
        } catch (IOException ignored) {
            return fallback;
        }
    }

    private static String parseTag(String content, String tag, String fallback) {
        int start = content.indexOf("<" + tag + ">");
        if (start < 0) return fallback;
        int end = content.indexOf("</" + tag + ">", start);
        if (end < 0) return fallback;
        return content.substring(start + tag.length() + 2, end).trim();
    }
}
