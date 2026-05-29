package io.github.jstruct.extract;

import com.github.javaparser.ParseProblemException;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.ConstructorDeclaration;
import com.github.javaparser.ast.body.EnumDeclaration;
import com.github.javaparser.ast.body.FieldDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.body.RecordDeclaration;
import com.github.javaparser.ast.body.TypeDeclaration;
import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.NameExpr;
import com.github.javaparser.ast.expr.ObjectCreationExpr;
import com.github.javaparser.ast.type.Type;
import io.github.jstruct.model.EntityFingerprint;
import io.github.jstruct.model.Relationship;
import io.github.jstruct.util.MavenModuleResolver;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

public class RelationshipExtractor {
    private final Map<String, EntityFingerprint> byFqn;
    private final Map<String, EntityFingerprint> bySimple;

    public RelationshipExtractor(List<EntityFingerprint> entities) {
        this.byFqn = new HashMap<>();
        this.bySimple = new HashMap<>();
        for (EntityFingerprint e : entities) {
            byFqn.put(e.fqn, e);
            bySimple.putIfAbsent(e.className, e);
        }
    }

    public List<Relationship> extractModule(MavenModuleResolver.ModuleInfo module) throws IOException {
        List<Relationship> result = new ArrayList<>();
        if (!Files.exists(module.sourceRoot())) return result;
        try (var stream = Files.walk(module.sourceRoot())) {
            for (Path file : stream.filter(p -> p.toString().endsWith(".java")).toList()) {
                result.addAll(extractFile(file, module));
            }
        }
        return aggregate(result);
    }

    public List<Relationship> extractFile(Path javaFile, MavenModuleResolver.ModuleInfo module) {
        try {
            return extract(StaticJavaParser.parse(javaFile));
        } catch (IOException | RuntimeException ex) {
            System.err.println("WARN: failed to parse relationships " + javaFile + ": " + ex.getMessage());
            return List.of();
        }
    }

    public List<Relationship> extract(CompilationUnit cu) {
        List<Relationship> relationships = new ArrayList<>();
        String pkg = cu.getPackageDeclaration().map(p -> p.getNameAsString()).orElse("");
        for (TypeDeclaration<?> type : cu.getTypes()) {
            String source = fqn(pkg, type.getNameAsString());
            EntityFingerprint srcEntity = byFqn.get(source);
            if (srcEntity == null) continue;
            extractTypeRelationships(type, srcEntity, relationships);
        }
        return aggregate(relationships);
    }

    private void extractTypeRelationships(TypeDeclaration<?> type, EntityFingerprint source,
                                          List<Relationship> out) {
        if (type instanceof ClassOrInterfaceDeclaration coid) {
            coid.getExtendedTypes().forEach(t -> add(out, source, resolveType(t), "EXTENDS", 1.0));
            coid.getImplementedTypes().forEach(t -> add(out, source, resolveType(t), "IMPLEMENTS", 1.0));
        }
        if (type instanceof EnumDeclaration ed) {
            ed.getImplementedTypes().forEach(t -> add(out, source, resolveType(t), "IMPLEMENTS", 1.0));
        }
        if (type instanceof RecordDeclaration rd) {
            rd.getImplementedTypes().forEach(t -> add(out, source, resolveType(t), "IMPLEMENTS", 1.0));
        }

        Map<String, EntityFingerprint> variableTypes = new HashMap<>();
        for (FieldDeclaration field : type.getFields()) {
            field.getVariables().forEach(v -> {
                EntityFingerprint target = resolveType(v.getType());
                if (target != null) {
                    variableTypes.put(v.getNameAsString(), target);
                    if (hasAnnotation(field.getAnnotations(), "Autowired") || hasAnnotation(field.getAnnotations(), "Inject")) {
                        add(out, source, target, "INJECTS", 1.0);
                    }
                    if (target.className.endsWith("Client") || target.roles.contains("RPC_CLIENT")) {
                        add(out, source, target, "RPC_CALLS", 1.0);
                    }
                }
            });
        }

        for (ConstructorDeclaration ctor : type.findAll(ConstructorDeclaration.class)) {
            if (hasAnnotation(ctor.getAnnotations(), "Autowired") || !ctor.getParameters().isEmpty()) {
                ctor.getParameters().forEach(p -> add(out, source, resolveType(p.getType()), "INJECTS", 1.0));
            }
        }

        for (MethodDeclaration method : type.findAll(MethodDeclaration.class)) {
            method.getParameters().forEach(p -> {
                EntityFingerprint target = resolveType(p.getType());
                if (target != null) variableTypes.put(p.getNameAsString(), target);
            });
            method.findAll(com.github.javaparser.ast.body.VariableDeclarator.class).forEach(v -> {
                EntityFingerprint target = resolveType(v.getType());
                if (target != null) variableTypes.put(v.getNameAsString(), target);
            });

            if (hasAnnotation(method.getAnnotations(), "Bean")) {
                add(out, source, resolveType(method.getType()), "CONFIGURES", 1.0);
            }
            if (hasAnnotation(method.getAnnotations(), "Transactional")) {
                add(out, source, source, "TX_BOUNDARY", 1.0);
            }
            for (AnnotationExpr ann : method.getAnnotations()) {
                if (hasAnyAnnotationName(ann, "EventListener", "KafkaListener", "RabbitListener")) {
                    add(out, source, source, "LISTENS", 1.0);
                }
            }
            if (source.roles.contains("ASPECT")) {
                for (AnnotationExpr ann : method.getAnnotations()) {
                    if (hasAnyAnnotationName(ann, "Around", "Before")) {
                        add(out, source, source, "ADVISED_BY", 1.0);
                    }
                }
            }
        }

        if (hasAnnotation(type.getAnnotations(), "Transactional")) {
            add(out, source, source, "TX_BOUNDARY", 1.0);
        }
        for (AnnotationExpr ann : type.getAnnotations()) {
            if (hasAnyAnnotationName(ann, "EventListener", "KafkaListener", "RabbitListener")) {
                add(out, source, source, "LISTENS", 1.0);
            }
        }

        type.findAll(ObjectCreationExpr.class).forEach(expr -> add(out, source, resolveType(expr.getType()), "INVOKES", 1.0));
        type.findAll(MethodCallExpr.class).forEach(call -> {
            Optional<EntityFingerprint> target = call.getScope()
                .filter(NameExpr.class::isInstance)
                .map(NameExpr.class::cast)
                .map(n -> variableTypes.get(n.getNameAsString()));
            target.ifPresent(t -> add(out, source, t, "INVOKES", 1.0));
        });
    }

    private EntityFingerprint resolveType(Type type) {
        String name = type.asString();
        while (name.endsWith("[]")) name = name.substring(0, name.length() - 2);
        int generic = name.indexOf('<');
        if (generic >= 0) name = name.substring(0, generic);
        name = name.strip();
        EntityFingerprint exact = byFqn.get(name);
        if (exact != null) return exact;
        int dot = name.lastIndexOf('.');
        String simple = dot >= 0 ? name.substring(dot + 1) : name;
        return bySimple.get(simple);
    }

    private void add(List<Relationship> out, EntityFingerprint source, EntityFingerprint target,
                     String type, double weight) {
        if (source == null || target == null) return;
        out.add(new Relationship(source.fqn, target.fqn, type, weight, source.module, target.module));
    }

    private boolean hasAnnotation(List<AnnotationExpr> annotations, String name) {
        return annotations.stream().anyMatch(a -> AnnotationRoleMapper.isAnnotationNamed(a, name));
    }

    private boolean hasAnyAnnotationName(AnnotationExpr annotation, String... names) {
        for (String name : names) {
            if (AnnotationRoleMapper.isAnnotationNamed(annotation, name)) return true;
        }
        return false;
    }

    private String fqn(String pkg, String className) {
        return pkg == null || pkg.isBlank() ? className : pkg + "." + className;
    }

    public static List<Relationship> aggregate(List<Relationship> input) {
        Map<String, Relationship> byKey = new LinkedHashMap<>();
        for (Relationship r : input) {
            if (r == null || r.source == null || r.target == null || Objects.equals(r.source, r.target) && !"TX_BOUNDARY".equals(r.type) && !"LISTENS".equals(r.type) && !"ADVISED_BY".equals(r.type)) {
                continue;
            }
            String key = r.source + "\n" + r.target + "\n" + r.type;
            Relationship existing = byKey.get(key);
            if (existing == null) {
                byKey.put(key, r);
            } else {
                existing.weight += r.weight;
            }
        }
        return new ArrayList<>(byKey.values());
    }
}
