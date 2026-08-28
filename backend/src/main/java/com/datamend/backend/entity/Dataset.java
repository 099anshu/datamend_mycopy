package com.datamend.backend.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "datasets")
public class Dataset {

    @Id
    @GeneratedValue
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "file_path", nullable = false)
    private String filePath;

    @Column(name = "row_count", nullable = false)
    private Integer rowCount;

    @Column(name = "column_count", nullable = false)
    private Integer columnCount;

    @Column(name = "source_type", nullable = false)
    private String sourceType = "TSDB";

    /** Identifier of the dataset within its source (e.g. the ml-service upload id). */
    @Column(name = "external_id")
    private String externalId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "profile", columnDefinition = "jsonb")
    private String profile;

    @Column(name = "uploaded_at")
    private OffsetDateTime uploadedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    protected Dataset() {}

    public Dataset(String name, String filePath, Integer rowCount, Integer columnCount) {
        this.name = name;
        this.filePath = filePath;
        this.rowCount = rowCount;
        this.columnCount = columnCount;
    }

    public Dataset(
            String name,
            String filePath,
            Integer rowCount,
            Integer columnCount,
            String sourceType,
            String externalId,
            String profile,
            OffsetDateTime uploadedAt) {
        this(name, filePath, rowCount, columnCount);
        this.sourceType = sourceType;
        this.externalId = externalId;
        this.profile = profile;
        this.uploadedAt = uploadedAt;
    }

    public UUID getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getFilePath() {
        return filePath;
    }

    public Integer getRowCount() {
        return rowCount;
    }

    public Integer getColumnCount() {
        return columnCount;
    }

    public String getSourceType() {
        return sourceType;
    }

    public String getExternalId() {
        return externalId;
    }

    public String getProfile() {
        return profile;
    }

    public OffsetDateTime getUploadedAt() {
        return uploadedAt;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    @PrePersist
    protected void onCreate() {
        this.createdAt = OffsetDateTime.now();
    }
}
