package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;

import java.util.List;

/**
 * Strategy interface for resolving time-series datasets from various sources
 * (e.g. TSDB, external REST APIs, Python libraries, object storage).
 */
public interface DatasetProvider {

    /**
     * Source identifier (e.g. "TSDB", "EXTERNAL_API", "PYTHON_LIB").
     */
    String getSourceType();

    /**
     * Check if this provider supports the given dataset name or URI scheme.
     */
    boolean supports(String datasetName);

    /**
     * Resolve a dataset entity representation with metadata.
     */
    Dataset resolveDataset(String datasetName, List<String> columns);
}
