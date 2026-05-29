package io.github.javacodeatlas.metrics;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.javacodeatlas.model.AtlasDocument;
import io.github.javacodeatlas.model.EntityFingerprint;
import io.github.javacodeatlas.model.Relationship;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.jgrapht.Graph;
import org.jgrapht.alg.scoring.PageRank;
import org.jgrapht.graph.DefaultWeightedEdge;
import org.junit.jupiter.api.Test;

class GraphAnalyzerTest {
    @Test
    void classGraphSupportsPageRankOnSimpleGraph() {
        AtlasDocument doc = document(
            List.of(entity("a.A", "app", "class"), entity("a.B", "app", "class"), entity("a.C", "app", "class")),
            List.of(
                relationship("a.A", "a.B", "USES", 1.0),
                relationship("a.C", "a.B", "USES", 1.0)));
        Graph<String, DefaultWeightedEdge> graph = new GraphAnalyzer(doc).classGraph();

        PageRank<String, DefaultWeightedEdge> pageRank = new PageRank<>(graph);

        assertTrue(pageRank.getVertexScore("a.B") > pageRank.getVertexScore("a.A"));
        assertTrue(pageRank.getVertexScore("a.B") > pageRank.getVertexScore("a.C"));
    }

    @Test
    void sccDetectsDirectedCyclesOnly() {
        AtlasDocument doc = document(
            List.of(entity("a.A", "app", "class"), entity("a.B", "app", "class"), entity("a.C", "app", "class")),
            List.of(
                relationship("a.A", "a.B", "USES", 1.0),
                relationship("a.B", "a.A", "USES", 1.0),
                relationship("a.B", "a.C", "USES", 1.0)));
        GraphAnalyzer analyzer = new GraphAnalyzer(doc);

        List<List<String>> cycles = analyzer.scc(analyzer.classGraph());

        assertEquals(1, cycles.size());
        assertEquals(List.of("a.A", "a.B"), cycles.get(0).stream().sorted().toList());
    }

    @Test
    void sccReturnsNoCyclesForAcyclicGraph() {
        AtlasDocument doc = document(
            List.of(entity("a.A", "app", "class"), entity("a.B", "app", "class"), entity("a.C", "app", "class")),
            List.of(
                relationship("a.A", "a.B", "USES", 1.0),
                relationship("a.B", "a.C", "USES", 1.0)));
        GraphAnalyzer analyzer = new GraphAnalyzer(doc);

        assertEquals(List.of(), analyzer.scc(analyzer.classGraph()));
    }

    @Test
    void martinMetricsClassifiesAiMatrixQuadrants() {
        AtlasDocument doc = document(
            List.of(
                entity("pain.Concrete", "pain", "class"),
                entity("useless.Api", "useless", "interface"),
                entity("normal.Concrete", "normal", "class"),
                entity("good.Api", "good", "interface"),
                entity("driver.One", "driver1", "class"),
                entity("driver.Two", "driver2", "class"),
                entity("driver.Three", "driver3", "class")),
            List.of(
                relationship("driver.One", "pain.Concrete", "USES", 1.0),
                relationship("driver.Two", "useless.Api", "USES", 1.0),
                relationship("normal.Concrete", "pain.Concrete", "USES", 1.0),
                relationship("good.Api", "useless.Api", "USES", 1.0),
                relationship("driver.Three", "good.Api", "USES", 1.0),
                relationship("good.Api", "normal.Concrete", "USES", 1.0)));
        GraphAnalyzer analyzer = new GraphAnalyzer(doc);

        Map<String, String> zones = analyzer.martinMetrics().stream()
            .collect(Collectors.toMap(GraphAnalyzer.ModuleMetric::module, GraphAnalyzer.ModuleMetric::zone));

        assertEquals("pain", zones.get("pain"));
        assertEquals("useless", zones.get("useless"));
        assertEquals("normal", zones.get("normal"));
        assertEquals("good", zones.get("good"));
    }

    @Test
    void classGraphAggregatesDuplicateRelationshipWeightsAndDegrees() {
        AtlasDocument doc = document(
            List.of(entity("a.A", "app", "class"), entity("a.B", "app", "class")),
            List.of(
                relationship("a.A", "a.B", "USES", 1.0),
                relationship("a.A", "a.B", "CALLS", 2.5)));
        GraphAnalyzer analyzer = new GraphAnalyzer(doc);
        Graph<String, DefaultWeightedEdge> graph = analyzer.classGraph();

        assertEquals(1, graph.edgeSet().size());
        assertEquals(3.5, graph.getEdgeWeight(graph.getEdge("a.A", "a.B")));
        assertEquals(0, analyzer.degrees(graph).get("a.A")[0]);
        assertEquals(1, analyzer.degrees(graph).get("a.A")[1]);
    }

    private static AtlasDocument document(List<EntityFingerprint> entities, List<Relationship> relationships) {
        AtlasDocument doc = new AtlasDocument();
        doc.entities.addAll(entities);
        doc.relationships.addAll(relationships);
        return doc;
    }

    private static EntityFingerprint entity(String fqn, String module, String kind) {
        EntityFingerprint entity = new EntityFingerprint();
        entity.fqn = fqn;
        entity.className = fqn.substring(fqn.lastIndexOf('.') + 1);
        entity.module = module;
        entity.kind = kind;
        return entity;
    }

    private static Relationship relationship(String source, String target, String type, double weight) {
        return new Relationship(source, target, type, weight, "", "");
    }
}
