package com.datamend.backend.entity;

import jakarta.persistence.*;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "anomalies")
public class Anomaly {

    @Id
    @GeneratedValue
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "analysis_id", nullable = false)
    private UUID analysisId;

    @Column(name = "timestamp", nullable = false)
    private OffsetDateTime timestamp;

    @Column(name = "column_name", nullable = false, length = 255)
    private String columnName;

    @Column(name = "value")
    private Double value;

    @Column(name = "score")
    private Double score;

    @Column(name = "severity", nullable = false, length = 32)
    private String severity;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    protected Anomaly() {}

    public Anomaly(UUID analysisId, OffsetDateTime timestamp, String columnName, Double value, Double score, String severity) {
        this.analysisId = analysisId;
        this.timestamp = timestamp;
        this.columnName = columnName;
        this.value = value;
        this.score = score;
        this.severity = severity;
    }

    public Anomaly(OffsetDateTime timestamp, String columnName, Double value, Double score, String severity) {
        this.timestamp = timestamp;
        this.columnName = columnName;
        this.value = value;
        this.score = score;
        this.severity = severity;
    }

    public UUID getId() {
        return id;
    }

    public UUID getAnalysisId() {
        return analysisId;
    }

    public void setAnalysisId(UUID analysisId) {
        this.analysisId = analysisId;
    }

    public OffsetDateTime getTimestamp() {
        return timestamp;
    }

    public String getColumnName() {
        return columnName;
    }

    public Double getValue() {
        return value;
    }

    public Double getScore() {
        return score;
    }

    public String getSeverity() {
        return severity;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    @PrePersist
    protected void onCreate() {
        this.createdAt = OffsetDateTime.now();
    }
}