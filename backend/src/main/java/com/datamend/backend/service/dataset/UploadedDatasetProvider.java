package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;
import tools.jackson.databind.ObjectMapper;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Resolves datasets that users uploaded through the ml-service dataset store.
 * The dataset name carried by an analysis request is the upload id.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class UploadedDatasetProvider implements DatasetProvider {

    public static final String SOURCE_TYPE = "UPLOAD";

    private final DatasetProxyService datasetProxyService;
    private final ObjectMapper objectMapper;

    public UploadedDatasetProvider(DatasetProxyService datasetProxyService, ObjectMapper objectMapper) {
        this.datasetProxyService = datasetProxyService;
        this.objectMapper = objectMapper;
    }

    @Override
    public String getSourceType() {
        return SOURCE_TYPE;
    }

    @Override
    public boolean supports(String sourceType) {
        return SOURCE_TYPE.equalsIgnoreCase(sourceType);
    }

    @Override
    public Dataset resolveDataset(String datasetId, List<String> columns) {
        Map<String, Object> metadata = datasetProxyService.get(datasetId);

        @SuppressWarnings("unchecked")
        Map<String, Object> profile = (Map<String, Object>) metadata.get("profile");
        String name = (String) metadata.getOrDefault("name", datasetId);
        int rowCount = intValue(profile, "rowCount");
        int columnCount = intValue(profile, "columnCount");

        return new Dataset(
                name,
                "upload://" + datasetId,
                rowCount,
                columnCount,
                SOURCE_TYPE,
                datasetId,
                serialize(profile),
                parseUploadedAt(metadata.get("uploadedAt")));
    }

    private int intValue(Map<String, Object> source, String key) {
        if (source == null) {
            return 0;
        }
        Object value = source.get(key);
        return value instanceof Number number ? number.intValue() : 0;
    }

    private OffsetDateTime parseUploadedAt(Object raw) {
        if (!(raw instanceof String text) || text.isBlank()) {
            return null;
        }
        return OffsetDateTime.parse(text);
    }

    private String serialize(Map<String, Object> profile) {
        if (profile == null) {
            return null;
        }
        return objectMapper.writeValueAsString(profile);
    }
}
