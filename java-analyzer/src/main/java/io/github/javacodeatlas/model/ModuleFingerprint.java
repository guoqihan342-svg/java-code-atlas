package io.github.javacodeatlas.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.ArrayList;
import java.util.List;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public class ModuleFingerprint {
    @JsonProperty("module")
    public String module;
    @JsonProperty("type")
    public String type;
    @JsonProperty("artifactId")
    public String artifactId;
    @JsonProperty("groupId")
    public String groupId;
    @JsonProperty("classes")
    public int classes;
    @JsonProperty("interfaces")
    public int interfaces;
    @JsonProperty("abstractClasses")
    public int abstractClasses;
    @JsonProperty("enums")
    public int enums;
    @JsonProperty("annotations")
    public int annotations;
    @JsonProperty("records")
    public int records;
    @JsonProperty("internalDeps")
    public int internalDeps;
    @JsonProperty("externalDeps")
    public int externalDeps;
    @JsonProperty("testClasses")
    public int testClasses;
    @JsonProperty("testRatio")
    public double testRatio;
    @JsonProperty("architectureRoles")
    public List<String> architectureRoles = new ArrayList<>();
}
