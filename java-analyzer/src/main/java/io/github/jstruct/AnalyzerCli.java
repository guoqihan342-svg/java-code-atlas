package io.github.jstruct;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import io.github.jstruct.extract.FingerprintExtractor;
import io.github.jstruct.extract.RelationshipExtractor;
import io.github.jstruct.metrics.MetricsCli;
import io.github.jstruct.model.JStructDocument;
import io.github.jstruct.model.EntityFingerprint;
import io.github.jstruct.model.ModuleFingerprint;
import io.github.jstruct.model.Relationship;
import io.github.jstruct.util.JdkVersionDetector;
import io.github.jstruct.util.MavenModuleResolver;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

@Command(
    name = "jstruct-analyzer",
    mixinStandardHelpOptions = true,
    subcommands = {AnalyzerCli.AnalyzeCommand.class, AnalyzerCli.MetricsCommand.class}
)
public class AnalyzerCli implements Runnable {
    public static void main(String[] args) {
        int code = new CommandLine(new AnalyzerCli()).execute(args);
        System.exit(code);
    }

    @Override
    public void run() {
        CommandLine.usage(this, System.out);
    }

    @Command(name = "analyze", mixinStandardHelpOptions = true)
    public static class AnalyzeCommand implements Callable<Integer> {
        @Option(names = "--root", required = true)
        Path root;
        @Option(names = {"--modules", "--module"}, split = ",")
        List<String> modules = new ArrayList<>();
        @Option(names = "--output", required = true)
        Path output;
        @Option(names = "--maven-home")
        Path mavenHome;
        @Option(names = "--resolve-symbols")
        boolean resolveSymbols;

        @Override
        public Integer call() throws Exception {
            List<MavenModuleResolver.ModuleInfo> moduleInfos = resolveModules(root, modules);
            FingerprintExtractor fingerprintExtractor = new FingerprintExtractor();
            List<EntityFingerprint> entities = new ArrayList<>();
            for (MavenModuleResolver.ModuleInfo module : moduleInfos) {
                entities.addAll(fingerprintExtractor.extractModule(module));
            }

            RelationshipExtractor relationshipExtractor = new RelationshipExtractor(entities);
            List<Relationship> relationships = new ArrayList<>();
            for (MavenModuleResolver.ModuleInfo module : moduleInfos) {
                relationships.addAll(relationshipExtractor.extractModule(module));
            }
            relationships = RelationshipExtractor.aggregate(relationships);

            JStructDocument doc = new JStructDocument();
            doc.entities = entities;
            doc.relationships = relationships;
            doc.modules = buildModuleFingerprints(root, moduleInfos, entities, relationships);
            doc.jstruct.version = JStructDocument.CURRENT_VERSION;
            doc.jstruct.generatedAt = Instant.now().toString();
            doc.jstruct.project = root.toAbsolutePath().getFileName().toString();
            doc.jstruct.jdkVersion = JdkVersionDetector.detect(root);
            doc.jstruct.totalModules = doc.modules.size();
            doc.jstruct.totalEntities = doc.entities.size();
            doc.jstruct.totalRelationships = doc.relationships.size();

            writeJson(output, doc);
            return 0;
        }
    }

    @Command(name = "metrics", mixinStandardHelpOptions = true)
    public static class MetricsCommand implements Callable<Integer> {
        @Option(names = "--input", required = true)
        Path input;
        @Option(names = "--output", required = true)
        Path output;
        @Option(names = "--report")
        Path report;
        @Option(names = "--mermaid")
        Path mermaid;

        @Override
        public Integer call() throws Exception {
            MetricsCli.run(input, output, report, mermaid);
            return 0;
        }
    }

    private static List<MavenModuleResolver.ModuleInfo> resolveModules(Path root, List<String> requested)
        throws IOException {
        if (requested == null || requested.isEmpty()) {
            return MavenModuleResolver.resolve(root);
        }

        Set<String> wanted = new LinkedHashSet<>();
        for (String item : requested) {
            if (item == null || item.isBlank()) continue;
            wanted.addAll(Arrays.stream(item.split(",")).map(String::trim).filter(s -> !s.isEmpty()).toList());
        }

        List<MavenModuleResolver.ModuleInfo> discovered = MavenModuleResolver.resolve(root);
        List<MavenModuleResolver.ModuleInfo> filtered = discovered.stream()
            .filter(m -> wanted.contains(m.artifactId()) || wanted.contains(root.relativize(m.moduleRoot()).toString()))
            .toList();
        if (!filtered.isEmpty()) return filtered;

        List<MavenModuleResolver.ModuleInfo> manual = new ArrayList<>();
        for (String name : wanted) {
            Path moduleRoot = root.resolve(name);
            Path src = moduleRoot.resolve("src/main/java");
            if (Files.exists(src)) {
                String packaging = Files.exists(moduleRoot.resolve("pom.xml"))
                    ? MavenModuleResolver.parsePackaging(moduleRoot.resolve("pom.xml")) : "jar";
                if (!"pom".equals(packaging)) {
                    manual.add(new MavenModuleResolver.ModuleInfo(name, packaging, moduleRoot, src));
                }
            }
        }
        return manual;
    }

    private static List<ModuleFingerprint> buildModuleFingerprints(
        Path root,
        List<MavenModuleResolver.ModuleInfo> modules,
        List<EntityFingerprint> entities,
        List<Relationship> relationships
    ) {
        List<ModuleFingerprint> result = new ArrayList<>();
        for (MavenModuleResolver.ModuleInfo info : modules) {
            ModuleFingerprint mf = new ModuleFingerprint();
            mf.module = info.artifactId();
            mf.type = info.packaging();
            mf.artifactId = MavenModuleResolver.parseArtifactId(info.moduleRoot().resolve("pom.xml"), info.artifactId());
            mf.groupId = MavenModuleResolver.parseGroupId(info.moduleRoot().resolve("pom.xml"), "");

            List<EntityFingerprint> ents = entities.stream()
                .filter(e -> info.artifactId().equals(e.module)).toList();
            mf.classes = (int) ents.stream().filter(e -> "class".equals(e.kind)).count();
            mf.interfaces = (int) ents.stream().filter(e -> "interface".equals(e.kind)).count();
            mf.abstractClasses = (int) ents.stream().filter(e -> "abstract".equals(e.kind)).count();
            mf.enums = (int) ents.stream().filter(e -> "enum".equals(e.kind)).count();
            mf.annotations = (int) ents.stream().filter(e -> "annotation".equals(e.kind)).count();
            mf.records = (int) ents.stream().filter(e -> "record".equals(e.kind)).count();
            mf.internalDeps = (int) relationships.stream()
                .filter(r -> info.artifactId().equals(r.module_source) && info.artifactId().equals(r.module_target)).count();
            mf.externalDeps = (int) relationships.stream()
                .filter(r -> info.artifactId().equals(r.module_source) && !info.artifactId().equals(r.module_target)).count();
            mf.testClasses = countTestClasses(info.moduleRoot());
            int prodCount = ents.size();
            mf.testRatio = prodCount == 0 ? 0.0 : (double) mf.testClasses / prodCount;
            mf.architectureRoles = ents.stream()
                .flatMap(e -> e.roles.stream())
                .distinct()
                .toList();
            result.add(mf);
        }
        return result;
    }

    private static int countTestClasses(Path moduleRoot) {
        Path testRoot = moduleRoot.resolve("src/test/java");
        if (!Files.exists(testRoot)) return 0;
        try (var stream = Files.walk(testRoot)) {
            return (int) stream.filter(p -> p.toString().endsWith(".java")).count();
        } catch (IOException ignored) {
            return 0;
        }
    }

    private static void writeJson(Path output, Object value) throws IOException {
        Path parent = output.toAbsolutePath().getParent();
        if (parent != null) Files.createDirectories(parent);
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        mapper.writeValue(output.toFile(), value);
    }
}
