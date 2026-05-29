package io.github.javastruct.metrics;

import io.github.javastruct.model.JavaStructDocument;
import io.github.javastruct.model.EntityFingerprint;
import io.github.javastruct.model.Relationship;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.jgrapht.Graph;
import org.jgrapht.graph.DefaultDirectedWeightedGraph;
import org.jgrapht.graph.DefaultWeightedEdge;

public class GraphAnalyzer {
    private final JavaStructDocument doc;

    public GraphAnalyzer(JavaStructDocument doc) {
        this.doc = doc;
    }

    public Graph<String, DefaultWeightedEdge> classGraph() {
        Graph<String, DefaultWeightedEdge> g = new DefaultDirectedWeightedGraph<>(DefaultWeightedEdge.class);
        doc.entities.forEach(e -> g.addVertex(e.fqn));
        for (Relationship r : doc.relationships) {
            if (!g.containsVertex(r.source)) g.addVertex(r.source);
            if (!g.containsVertex(r.target)) g.addVertex(r.target);
            DefaultWeightedEdge edge = g.getEdge(r.source, r.target);
            if (edge == null) {
                edge = g.addEdge(r.source, r.target);
                if (edge != null) g.setEdgeWeight(edge, r.weight);
            } else {
                g.setEdgeWeight(edge, g.getEdgeWeight(edge) + r.weight);
            }
        }
        return g;
    }

    public Graph<String, DefaultWeightedEdge> moduleGraph() {
        Graph<String, DefaultWeightedEdge> g = new DefaultDirectedWeightedGraph<>(DefaultWeightedEdge.class);
        Set<String> modules = doc.entities.stream().map(e -> e.module).collect(Collectors.toSet());
        modules.forEach(g::addVertex);
        for (Relationship r : doc.relationships) {
            String srcMod = entityModule(r.source);
            String tgtMod = entityModule(r.target);
            if (srcMod == null || tgtMod == null) continue;
            if (srcMod.equals(tgtMod)) continue;
            DefaultWeightedEdge edge = g.getEdge(srcMod, tgtMod);
            if (edge == null) {
                edge = g.addEdge(srcMod, tgtMod);
                if (edge != null) g.setEdgeWeight(edge, r.weight);
            } else {
                g.setEdgeWeight(edge, g.getEdgeWeight(edge) + r.weight);
            }
        }
        return g;
    }

    private String entityModule(String fqn) {
        return doc.entities.stream()
            .filter(e -> e.fqn.equals(fqn))
            .findFirst().map(e -> e.module).orElse(null);
    }

    public Map<String, int[]> degrees(Graph<String, ?> g) {
        Map<String, int[]> result = new HashMap<>();
        for (String v : g.vertexSet()) {
            result.put(v, new int[]{g.inDegreeOf(v), g.outDegreeOf(v)});
        }
        return result;
    }

    public List<List<String>> scc(Graph<String, ?> g) {
        var alg = new org.jgrapht.alg.connectivity.KosarajuStrongConnectivityInspector<>(g);
        return alg.stronglyConnectedSets().stream()
            .filter(set -> set.size() > 1)
            .map(ArrayList::new)
            .collect(Collectors.toList());
    }

    public record ModuleMetric(
        String module, int ca, int ce, double instability,
        double abstractness, double distance, String zone) {}

    public List<ModuleMetric> martinMetrics() {
        Graph<String, DefaultWeightedEdge> mg = moduleGraph();
        List<ModuleMetric> result = new ArrayList<>();
        for (String mod : mg.vertexSet()) {
            int ca = mg.inDegreeOf(mod);
            int ce = mg.outDegreeOf(mod);
            double i = (ca + ce) == 0 ? 0 : (double) ce / (ca + ce);
            double a = abstractness(mod);
            double d = Math.abs(a + i - 1);
            String zone = classifyZone(i, a);
            result.add(new ModuleMetric(mod, ca, ce, i, a, d, zone));
        }
        return result;
    }

    private double abstractness(String module) {
        long total = doc.entities.stream().filter(e -> e.module.equals(module)).count();
        if (total == 0) return 1.0;
        long absCount = doc.entities.stream()
            .filter(e -> e.module.equals(module))
            .filter(e -> "abstract".equals(e.kind) || "interface".equals(e.kind)).count();
        return (double) absCount / total;
    }

    private String classifyZone(double i, double a) {
        if (i < 0.5 && a < 0.5) return "pain";
        if (i >= 0.5 && a >= 0.5) return "good";
        if (i < 0.5 && a >= 0.5) return "useless";
        return "normal";
    }

    public record Hotspot(String fqn, double score, String severity) {}

    public List<Hotspot> hotspots(int topN) {
        Graph<String, DefaultWeightedEdge> cg = classGraph();
        return doc.entities.stream().map(e -> {
            double score = cg.inDegreeOf(e.fqn) * 1.0
                + cg.outDegreeOf(e.fqn) * 0.5
                + e.cyclomaticComplexityMax * 0.3
                + e.loc * 0.01
                + e.transactionalMethods.size() * 0.2
                + e.implements_.size() * 0.1;
            String severity = score > 20 ? "red" : score > 10 ? "yellow" : "green";
            return new Hotspot(e.fqn, score, severity);
        }).sorted((a, b) -> Double.compare(b.score, a.score))
          .limit(topN).collect(Collectors.toList());
    }

    public record BoundaryScore(
        String module, int total, double interfaceRatio,
        int cycles, int publicMethods, int score, String grade) {}

    public List<BoundaryScore> boundaryScores() {
        Graph<String, DefaultWeightedEdge> mg = moduleGraph();
        List<List<String>> cycles = scc(mg);
        Set<String> cyclicModules = cycles.stream().flatMap(List::stream).collect(Collectors.toSet());

        return mg.vertexSet().stream().map(mod -> {
            List<EntityFingerprint> ents = doc.entities.stream()
                .filter(e -> e.module.equals(mod)).toList();
            long interfaces = ents.stream()
                .filter(e -> "interface".equals(e.kind) || "abstract".equals(e.kind)).count();
            double ir = ents.isEmpty() ? 0 : (double) interfaces / ents.size();
            int pubMethods = ents.stream().mapToInt(e -> e.publicMethods).sum();
            int cyclePenalty = cyclicModules.contains(mod)
                ? cycles.stream()
                    .filter(c -> c.contains(mod))
                    .mapToInt(List::size).max().orElse(0) * 5
                : 0;

            int score = 100 - cyclePenalty
                - Math.max(0, (int) ((0.25 - Math.abs(ir - 0.25)) * 100))
                - Math.min(20, pubMethods / 50);
            String grade = score >= 80 ? "良好"
                : score >= 60 ? "一般" : score >= 40 ? "弱" : "无边界";

            return new BoundaryScore(
                mod, ents.size(), ir,
                cyclicModules.contains(mod) ? 1 : 0,
                pubMethods, Math.max(0, score), grade);
        }).collect(Collectors.toList());
    }
}
