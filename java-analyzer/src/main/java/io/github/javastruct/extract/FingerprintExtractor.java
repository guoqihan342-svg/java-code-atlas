package io.github.javastruct.extract;

import com.github.javaparser.ParseProblemException;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.body.AnnotationDeclaration;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.ConstructorDeclaration;
import com.github.javaparser.ast.body.EnumDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.body.RecordDeclaration;
import com.github.javaparser.ast.body.TypeDeclaration;
import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.stmt.CatchClause;
import com.github.javaparser.ast.stmt.DoStmt;
import com.github.javaparser.ast.stmt.ForEachStmt;
import com.github.javaparser.ast.stmt.ForStmt;
import com.github.javaparser.ast.stmt.IfStmt;
import com.github.javaparser.ast.stmt.SwitchEntry;
import com.github.javaparser.ast.stmt.WhileStmt;
import io.github.javastruct.model.EntityFingerprint;
import io.github.javastruct.util.MavenModuleResolver;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;

public class FingerprintExtractor {
    public List<EntityFingerprint> extractModule(MavenModuleResolver.ModuleInfo module) throws IOException {
        List<EntityFingerprint> result = new ArrayList<>();
        if (!Files.exists(module.sourceRoot())) return result;
        try (var stream = Files.walk(module.sourceRoot())) {
            for (Path file : stream.filter(p -> p.toString().endsWith(".java")).toList()) {
                result.addAll(extractFile(file, module));
            }
        }
        return result;
    }

    public List<EntityFingerprint> extractFile(Path javaFile, MavenModuleResolver.ModuleInfo module) {
        try {
            return extract(StaticJavaParser.parse(javaFile), module);
        } catch (IOException | RuntimeException ex) {
            System.err.println("WARN: failed to parse " + javaFile + ": " + ex.getMessage());
            return List.of();
        }
    }

    public List<EntityFingerprint> extract(CompilationUnit cu, MavenModuleResolver.ModuleInfo module) {
        String pkg = cu.getPackageDeclaration().map(p -> p.getNameAsString()).orElse("");
        List<EntityFingerprint> result = new ArrayList<>();
        for (TypeDeclaration<?> type : cu.getTypes()) {
            extractType(type, pkg, module).ifPresent(result::add);
        }
        return result;
    }

    private Optional<EntityFingerprint> extractType(TypeDeclaration<?> type, String pkg,
                                                    MavenModuleResolver.ModuleInfo module) {
        EntityFingerprint fp = new EntityFingerprint();
        fp.className = type.getNameAsString();
        fp.javaPackage = pkg;
        fp.fqn = pkg.isBlank() ? fp.className : pkg + "." + fp.className;
        fp.module = module.artifactId();
        fp.modulePath = module.moduleRoot().toString();
        fp.kind = kind(type);
        fp.modifiers = type.getModifiers().stream()
            .map(m -> m.getKeyword().asString()).toList();

        Set<String> roles = new LinkedHashSet<>();
        for (AnnotationExpr ann : type.getAnnotations()) {
            roles.addAll(AnnotationRoleMapper.resolve(ann));
        }
        fp.roles = new ArrayList<>(roles);

        if (type instanceof ClassOrInterfaceDeclaration coid) {
            fp.extends_ = coid.getExtendedTypes().stream().map(Object::toString).toList();
            fp.implements_ = coid.getImplementedTypes().stream().map(Object::toString).toList();
        }
        if (type instanceof EnumDeclaration ed) {
            fp.implements_ = ed.getImplementedTypes().stream().map(Object::toString).toList();
        }
        if (type instanceof RecordDeclaration rd) {
            fp.implements_ = rd.getImplementedTypes().stream().map(Object::toString).toList();
        }

        List<MethodDeclaration> methods = type.findAll(MethodDeclaration.class);
        fp.methods = methods.size();
        fp.publicMethods = (int) methods.stream().filter(MethodDeclaration::isPublic).count();
        fp.getters = (int) methods.stream().filter(this::isGetter).count();
        fp.setters = (int) methods.stream().filter(this::isSetter).count();
        fp.constructors = type.findAll(ConstructorDeclaration.class).size();
        fp.overrides = (int) methods.stream().filter(m -> hasAnnotation(m.getAnnotations(), "Override")).count();

        fp.transactionalMethods = methods.stream()
            .filter(m -> hasAnnotation(m.getAnnotations(), "Transactional"))
            .map(MethodDeclaration::getNameAsString)
            .toList();
        for (MethodDeclaration m : methods) {
            for (AnnotationExpr ann : m.getAnnotations()) {
                if (AnnotationRoleMapper.isAnnotationNamed(ann, "Transactional") && !fp.roles.contains("TRANSACTIONAL")) {
                    fp.roles.add("TRANSACTIONAL");
                }
                if (AnnotationRoleMapper.isAnnotationNamed(ann, "Bean") && !fp.roles.contains("CONFIG")) {
                    fp.roles.add("CONFIG");
                }
            }
        }

        fp.fieldInjection = type.getFields().stream()
            .anyMatch(f -> hasAnnotation(f.getAnnotations(), "Autowired") || hasAnnotation(f.getAnnotations(), "Inject"));
        fp.constructorInjection = type.findAll(ConstructorDeclaration.class).stream()
            .anyMatch(c -> hasAnnotation(c.getAnnotations(), "Autowired") || !c.getParameters().isEmpty());
        int fieldDeps = type.getFields().stream()
            .filter(f -> hasAnnotation(f.getAnnotations(), "Autowired") || hasAnnotation(f.getAnnotations(), "Inject"))
            .mapToInt(f -> f.getVariables().size()).sum();
        int ctorDeps = type.findAll(ConstructorDeclaration.class).stream()
            .filter(c -> hasAnnotation(c.getAnnotations(), "Autowired") || !c.getParameters().isEmpty())
            .mapToInt(c -> c.getParameters().size()).sum();
        fp.injectedDeps = fieldDeps + ctorDeps;

        fp.loc = lineSpan(type);
        List<Integer> methodLengths = methods.stream().map(this::lineSpan).toList();
        fp.maxMethodLength = methodLengths.stream().mapToInt(Integer::intValue).max().orElse(0);
        fp.avgMethodLength = methodLengths.stream().mapToInt(Integer::intValue).average().orElse(0.0);
        fp.cyclomaticComplexityMax = methods.stream().mapToInt(this::cyclomaticComplexity).max().orElse(0);
        fp.nestedDepthMax = methods.stream().mapToInt(m -> nestedDepth(m, 0)).max().orElse(0);

        fp.eventListenerTypes = type.findAll(AnnotationExpr.class).stream()
            .filter(a -> hasAnyAnnotationName(a, "EventListener", "KafkaListener", "RabbitListener"))
            .map(AnnotationExpr::getNameAsString)
            .distinct()
            .toList();

        return Optional.of(fp);
    }

    private String kind(TypeDeclaration<?> type) {
        if (type instanceof AnnotationDeclaration) return "annotation";
        if (type instanceof EnumDeclaration) return "enum";
        if (type instanceof RecordDeclaration) return "record";
        if (type instanceof ClassOrInterfaceDeclaration coid) {
            if (coid.isInterface()) return "interface";
            if (coid.isAbstract()) return "abstract";
        }
        return "class";
    }

    private boolean isGetter(MethodDeclaration m) {
        String n = m.getNameAsString();
        return m.getParameters().isEmpty()
            && !m.getType().isVoidType()
            && ((n.startsWith("get") && n.length() > 3) || (n.startsWith("is") && n.length() > 2));
    }

    private boolean isSetter(MethodDeclaration m) {
        String n = m.getNameAsString();
        return n.startsWith("set") && n.length() > 3
            && m.getParameters().size() == 1
            && m.getType().isVoidType();
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

    private int lineSpan(Node node) {
        if (node.getBegin().isPresent() && node.getEnd().isPresent()) {
            return Math.max(1, node.getEnd().get().line - node.getBegin().get().line + 1);
        }
        return 0;
    }

    private int cyclomaticComplexity(MethodDeclaration method) {
        int score = 1;
        score += method.findAll(IfStmt.class).size();
        score += method.findAll(ForStmt.class).size();
        score += method.findAll(ForEachStmt.class).size();
        score += method.findAll(WhileStmt.class).size();
        score += method.findAll(DoStmt.class).size();
        score += method.findAll(CatchClause.class).size();
        score += method.findAll(SwitchEntry.class).size();
        String text = method.toString().toLowerCase(Locale.ROOT);
        score += count(text, "&&") + count(text, "||") + count(text, "?");
        return score;
    }

    private int count(String text, String needle) {
        int c = 0;
        for (int i = text.indexOf(needle); i >= 0; i = text.indexOf(needle, i + needle.length())) c++;
        return c;
    }

    private int nestedDepth(Node node, int depth) {
        int next = isControlNode(node) ? depth + 1 : depth;
        int max = next;
        for (Node child : node.getChildNodes()) {
            max = Math.max(max, nestedDepth(child, next));
        }
        return max;
    }

    private boolean isControlNode(Node node) {
        return node instanceof IfStmt || node instanceof ForStmt || node instanceof ForEachStmt
            || node instanceof WhileStmt || node instanceof DoStmt || node instanceof SwitchEntry
            || node instanceof CatchClause;
    }
}
