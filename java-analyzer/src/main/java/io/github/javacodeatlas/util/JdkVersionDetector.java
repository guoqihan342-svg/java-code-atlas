package io.github.javacodeatlas.util;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class JdkVersionDetector {
    public static String detect(Path projectRoot) {
        Path pom = projectRoot.resolve("pom.xml");
        if (Files.exists(pom)) {
            String v = fromPom(pom);
            if (v != null) return v;
        }

        for (String name : new String[]{"build.gradle", "build.gradle.kts"}) {
            Path gradle = projectRoot.resolve(name);
            if (Files.exists(gradle)) {
                String v = fromGradle(gradle);
                if (v != null) return v;
            }
        }

        Path jv = projectRoot.resolve(".java-version");
        if (Files.exists(jv)) {
            try {
                return Files.readString(jv).trim();
            } catch (IOException ignored) {}
        }

        return System.getProperty("java.version");
    }

    private static String fromPom(Path pom) {
        try {
            String content = Files.readString(pom);
            Pattern p = Pattern.compile("<maven\\.compiler\\.(release|source)>\\s*(\\d+)\\s*</");
            Matcher m = p.matcher(content);
            if (m.find()) return m.group(2);
        } catch (IOException ignored) {}
        return null;
    }

    private static String fromGradle(Path gradle) {
        try {
            String content = Files.readString(gradle);
            Pattern p = Pattern.compile("(source|target)Compatibility\\s*=\\s*['\"]?(\\d+\\.?\\d*)['\"]?");
            Matcher m = p.matcher(content);
            if (m.find()) return m.group(2);
        } catch (IOException ignored) {}
        return null;
    }
}
