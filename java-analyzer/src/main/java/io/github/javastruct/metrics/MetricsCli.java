package io.github.javastruct.metrics;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import io.github.javastruct.model.JavaStructDocument;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.jgrapht.Graph;
import org.jgrapht.graph.DefaultWeightedEdge;

public class MetricsCli {
    public static MetricsDocument compute(JavaStructDocument doc) {
        GraphAnalyzer analyzer = new GraphAnalyzer(doc);
        Graph<String, DefaultWeightedEdge> classGraph = analyzer.classGraph();
        Graph<String, DefaultWeightedEdge> moduleGraph = analyzer.moduleGraph();
        MetricsDocument metrics = new MetricsDocument();
        metrics.java_struct = doc.java_struct;
        metrics.classDegrees = analyzer.degrees(classGraph);
        metrics.moduleDegrees = analyzer.degrees(moduleGraph);
        metrics.classCycles = analyzer.scc(classGraph);
        metrics.moduleCycles = analyzer.scc(moduleGraph);
        metrics.martin = analyzer.martinMetrics();
        metrics.hotspots = analyzer.hotspots(50);
        metrics.boundaries = analyzer.boundaryScores();
        return metrics;
    }

    public static void run(Path input, Path output, Path report, Path mermaid) throws IOException {
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        JavaStructDocument doc = mapper.readValue(input.toFile(), JavaStructDocument.class);
        MetricsDocument metrics = compute(doc);
        Files.createDirectories(output.toAbsolutePath().getParent());
        mapper.writeValue(output.toFile(), metrics);
        if (report != null) {
            Path parent = report.toAbsolutePath().getParent();
            if (parent != null) Files.createDirectories(parent);
            Files.writeString(report, renderReport(doc, metrics));
        }
        if (mermaid != null) {
            Path parent = mermaid.toAbsolutePath().getParent();
            if (parent != null) Files.createDirectories(parent);
            Files.writeString(mermaid, renderMermaid(doc));
        }
    }

    public static String renderReport(JavaStructDocument doc, MetricsDocument metrics) {
        StringBuilder sb = new StringBuilder();
        sb.append("# JavaStruct Metrics\n\n");
        sb.append("- Project: ").append(doc.java_struct.project).append('\n');
        sb.append("- Modules: ").append(doc.java_struct.totalModules).append('\n');
        sb.append("- Entities: ").append(doc.java_struct.totalEntities).append('\n');
        sb.append("- Relationships: ").append(doc.java_struct.totalRelationships).append("\n\n");
        sb.append("## Hotspots\n\n");
        for (GraphAnalyzer.Hotspot h : metrics.hotspots.stream().limit(20).toList()) {
            sb.append("- ").append(h.fqn()).append(" score=").append(String.format("%.2f", h.score()))
                .append(" severity=").append(h.severity()).append('\n');
        }
        sb.append("\n## Module Metrics\n\n");
        for (GraphAnalyzer.ModuleMetric m : metrics.martin) {
            sb.append("- ").append(m.module()).append(" Ca=").append(m.ca()).append(" Ce=").append(m.ce())
                .append(" I=").append(String.format("%.2f", m.instability()))
                .append(" A=").append(String.format("%.2f", m.abstractness()))
                .append(" zone=").append(m.zone()).append('\n');
        }
        return sb.toString();
    }

    public static String renderMermaid(JavaStructDocument doc) {
        StringBuilder sb = new StringBuilder("graph LR\n");
        doc.relationships.stream()
            .filter(r -> r.module_source != null && r.module_target != null && !r.module_source.equals(r.module_target))
            .forEach(r -> sb.append("  ").append(safe(r.module_source)).append(" -->|").append(r.type)
                .append("| ").append(safe(r.module_target)).append('\n'));
        return sb.toString();
    }

    private static String safe(String value) {
        return value.replaceAll("[^A-Za-z0-9_]", "_");
    }

    public static class MetricsDocument {
        @JsonProperty("java_struct")
        public JavaStructDocument.JavaStructMeta java_struct;
        @JsonProperty("classDegrees")
        public Map<String, int[]> classDegrees;
        @JsonProperty("moduleDegrees")
        public Map<String, int[]> moduleDegrees;
        @JsonProperty("classCycles")
        public List<List<String>> classCycles;
        @JsonProperty("moduleCycles")
        public List<List<String>> moduleCycles;
        @JsonProperty("martin")
        public List<GraphAnalyzer.ModuleMetric> martin;
        @JsonProperty("hotspots")
        public List<GraphAnalyzer.Hotspot> hotspots;
        @JsonProperty("boundaries")
        public List<GraphAnalyzer.BoundaryScore> boundaries;
    }
}
