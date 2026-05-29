package io.github.javastruct.extract;

import com.github.javaparser.ast.expr.AnnotationExpr;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class AnnotationRoleMapper {
    private static final Map<String, List<String>> DIRECT_MAP = Map.ofEntries(
        Map.entry("org.springframework.web.bind.annotation.RestController", List.of("REST_ENTRY")),
        Map.entry("org.springframework.stereotype.Controller", List.of("MVC_ENTRY")),
        Map.entry("org.springframework.stereotype.Service", List.of("BUSINESS_LOGIC", "SPRING_BEAN")),
        Map.entry("org.springframework.stereotype.Component", List.of("BUSINESS_LOGIC", "SPRING_BEAN")),
        Map.entry("org.springframework.stereotype.Repository", List.of("DATA_ACCESS", "SPRING_BEAN")),
        Map.entry("org.springframework.context.annotation.Configuration", List.of("CONFIG", "SPRING_BEAN")),
        Map.entry("org.springframework.transaction.annotation.Transactional", List.of("TRANSACTIONAL")),
        Map.entry("org.springframework.kafka.annotation.KafkaListener", List.of("MESSAGE_CONSUMER")),
        Map.entry("org.springframework.amqp.rabbit.annotation.RabbitListener", List.of("MESSAGE_CONSUMER")),
        Map.entry("org.springframework.scheduling.annotation.Scheduled", List.of("SCHEDULED_TASK")),
        Map.entry("org.springframework.cloud.openfeign.FeignClient", List.of("RPC_CLIENT")),
        Map.entry("org.aspectj.lang.annotation.Aspect", List.of("ASPECT")),
        Map.entry("org.springframework.web.bind.annotation.ControllerAdvice", List.of("GLOBAL_ADVICE")),
        Map.entry("jakarta.persistence.Entity", List.of("PERSISTENCE_MODEL")),
        Map.entry("javax.persistence.Entity", List.of("PERSISTENCE_MODEL")),
        Map.entry("org.springframework.boot.autoconfigure.SpringBootApplication", List.of("CONFIG", "SPRING_BEAN"))
    );

    private static final Map<String, List<String>> META_UNWRAP = Map.of(
        "org.springframework.boot.autoconfigure.SpringBootApplication",
        List.of("CONFIG", "SPRING_BEAN")
    );

    public static List<String> resolve(AnnotationExpr annotation) {
        String name = annotation.getNameAsString();
        Set<String> roles = new LinkedHashSet<>();

        for (var entry : DIRECT_MAP.entrySet()) {
            if (matches(name, entry.getKey())) {
                roles.addAll(entry.getValue());
            }
        }
        for (var entry : META_UNWRAP.entrySet()) {
            if (matches(name, entry.getKey())) {
                roles.addAll(entry.getValue());
            }
        }

        return new ArrayList<>(roles);
    }

    public static boolean isAnnotationNamed(AnnotationExpr annotation, String simpleOrFqn) {
        return matches(annotation.getNameAsString(), simpleOrFqn);
    }

    private static boolean matches(String actual, String expected) {
        return actual.equals(expected) || actual.equals(shortName(expected)) || actual.endsWith("." + shortName(expected));
    }

    private static String shortName(String fqn) {
        int lastDot = fqn.lastIndexOf('.');
        return lastDot >= 0 ? fqn.substring(lastDot + 1) : fqn;
    }
}
