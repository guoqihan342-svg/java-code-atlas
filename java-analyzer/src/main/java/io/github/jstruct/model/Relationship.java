package io.github.jstruct.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public class Relationship {
    @JsonProperty("source")
    public String source;
    @JsonProperty("target")
    public String target;
    @JsonProperty("type")
    public String type;
    @JsonProperty("weight")
    public double weight;
    @JsonProperty("module_source")
    public String module_source;
    @JsonProperty("module_target")
    public String module_target;

    public Relationship() {}

    public Relationship(String source, String target, String type, double weight,
                        String moduleSource, String moduleTarget) {
        this.source = source;
        this.target = target;
        this.type = type;
        this.weight = weight;
        this.module_source = moduleSource;
        this.module_target = moduleTarget;
    }
}
