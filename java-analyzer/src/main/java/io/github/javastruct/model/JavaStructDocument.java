package io.github.javastruct.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import java.util.ArrayList;
import java.util.List;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
@JsonPropertyOrder({"java_struct", "modules", "entities", "relationships"})
public class JavaStructDocument {
    public static final String CURRENT_VERSION = "1.0.0";

    @JsonProperty("java_struct")
    public JavaStructMeta java_struct = new JavaStructMeta();
    @JsonProperty("modules")
    public List<ModuleFingerprint> modules = new ArrayList<>();
    @JsonProperty("entities")
    public List<EntityFingerprint> entities = new ArrayList<>();
    @JsonProperty("relationships")
    public List<Relationship> relationships = new ArrayList<>();

    @JsonInclude(JsonInclude.Include.NON_EMPTY)
    public static class JavaStructMeta {
        @JsonProperty("version")
        public String version = CURRENT_VERSION;
        @JsonProperty("generatedAt")
        public String generatedAt;
        @JsonProperty("project")
        public String project;
        @JsonProperty("jdkVersion")
        public String jdkVersion;
        @JsonProperty("totalModules")
        public int totalModules;
        @JsonProperty("totalEntities")
        public int totalEntities;
        @JsonProperty("totalRelationships")
        public int totalRelationships;
    }
}
