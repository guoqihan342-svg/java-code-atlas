package io.github.javacodeatlas.extract;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.expr.MarkerAnnotationExpr;
import java.util.List;
import org.junit.jupiter.api.Test;

class AnnotationRoleMapperTest {
    @Test
    void restControllerResolvesToRestEntry() {
        assertEquals(List.of("REST_ENTRY"), AnnotationRoleMapper.resolve(annotation("RestController")));
    }

    @Test
    void serviceResolvesToBusinessLogicAndSpringBean() {
        assertEquals(List.of("BUSINESS_LOGIC", "SPRING_BEAN"), AnnotationRoleMapper.resolve(annotation("Service")));
    }

    @Test
    void repositoryResolvesToDataAccessAndSpringBean() {
        assertEquals(List.of("DATA_ACCESS", "SPRING_BEAN"), AnnotationRoleMapper.resolve(annotation("Repository")));
    }

    @Test
    void feignClientResolvesToRpcClient() {
        assertEquals(List.of("RPC_CLIENT"), AnnotationRoleMapper.resolve(annotation("FeignClient")));
    }

    @Test
    void springBootApplicationResolvesMetaAnnotationRoles() {
        assertEquals(List.of("CONFIG", "SPRING_BEAN"), AnnotationRoleMapper.resolve(annotation("SpringBootApplication")));
    }

    @Test
    void unknownAnnotationReturnsEmptyList() {
        assertEquals(List.of(), AnnotationRoleMapper.resolve(annotation("CustomThing")));
    }

    @Test
    void shortNameMatchingAcceptsFullyQualifiedSpringAnnotation() {
        assertEquals(
            List.of("BUSINESS_LOGIC", "SPRING_BEAN"),
            AnnotationRoleMapper.resolve(annotation("org.springframework.stereotype.Service")));
    }

    @Test
    void isAnnotationNamedMatchesSimpleAndFullyQualifiedNames() {
        AnnotationExpr annotation = annotation("org.springframework.stereotype.Service");

        assertTrue(AnnotationRoleMapper.isAnnotationNamed(annotation, "Service"));
        assertTrue(AnnotationRoleMapper.isAnnotationNamed(annotation, "org.springframework.stereotype.Service"));
        assertFalse(AnnotationRoleMapper.isAnnotationNamed(annotation, "Repository"));
    }

    private static AnnotationExpr annotation(String name) {
        return new MarkerAnnotationExpr(name);
    }
}
