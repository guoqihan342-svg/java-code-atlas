package io.github.javacodeatlas.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.ArrayList;
import java.util.List;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public class EntityFingerprint {
    @JsonProperty("fqn")
    public String fqn;
    @JsonProperty("className")
    public String className;
    @JsonProperty("module")
    public String module;
    @JsonProperty("modulePath")
    public String modulePath;
    @JsonProperty("javaPackage")
    public String javaPackage;
    @JsonProperty("kind")
    public String kind;
    @JsonProperty("modifiers")
    public List<String> modifiers = new ArrayList<>();
    @JsonProperty("roles")
    public List<String> roles = new ArrayList<>();
    @JsonProperty("extends_")
    public List<String> extends_ = new ArrayList<>();
    @JsonProperty("implements_")
    public List<String> implements_ = new ArrayList<>();
    @JsonProperty("methods")
    public int methods;
    @JsonProperty("publicMethods")
    public int publicMethods;
    @JsonProperty("getters")
    public int getters;
    @JsonProperty("setters")
    public int setters;
    @JsonProperty("constructors")
    public int constructors;
    @JsonProperty("overrides")
    public int overrides;
    @JsonProperty("injectedDeps")
    public int injectedDeps;
    @JsonProperty("constructorInjection")
    public boolean constructorInjection;
    @JsonProperty("fieldInjection")
    public boolean fieldInjection;
    @JsonProperty("transactionalMethods")
    public List<String> transactionalMethods = new ArrayList<>();
    @JsonProperty("loc")
    public int loc;
    @JsonProperty("avgMethodLength")
    public double avgMethodLength;
    @JsonProperty("maxMethodLength")
    public int maxMethodLength;
    @JsonProperty("cyclomaticComplexityMax")
    public int cyclomaticComplexityMax;
    @JsonProperty("nestedDepthMax")
    public int nestedDepthMax;
    @JsonProperty("eventListenerTypes")
    public List<String> eventListenerTypes = new ArrayList<>();
}
