package com.datamend.backend.entity;

import jakarta.persistence.*;
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

    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    protected Dataset() {}

    public Dataset(String name, String filePath, Integer rowCount, Integer columnCount) {
        this.name = name;
        this.filePath = filePath;
        this.rowCount = rowCount;
        this.columnCount = columnCount;
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

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    @PrePersist
    protected void onCreate() {
        this.createdAt = OffsetDateTime.now();
    }
}