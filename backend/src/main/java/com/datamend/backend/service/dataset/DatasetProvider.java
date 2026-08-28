package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;

import java.util.List;

/**
 * Strategy interface for resolving time-series datasets from various sources
 * (e.g. TSDB, user uploads, external REST APIs, object storage).
 */
public interface DatasetProvider {

    /**
     * Source identifier (e.g. "TSDB", "UPLOAD", "EXTERNAL_API").
     */
    String getSourceType();

    /**
     * Check if this provider handles the given source identifier.
     */
    boolean supports(String sourceType);

    /**
     * Resolve a dataset entity representation with metadata.
     */
    Dataset resolveDataset(String datasetName, List<String> columns);
}
