package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@Order(Ordered.LOWEST_PRECEDENCE)
public class TsdbDatasetProvider implements DatasetProvider {

    public static final String SOURCE_TYPE = "TSDB";

    @Override
    public String getSourceType() {
        return SOURCE_TYPE;
    }

    @Override
    public boolean supports(String sourceType) {
        return sourceType == null || sourceType.isBlank() || SOURCE_TYPE.equalsIgnoreCase(sourceType);
    }

    @Override
    public Dataset resolveDataset(String datasetName, List<String> columns) {
        String cleanName = datasetName.startsWith("tsdb://")
                ? datasetName.substring(7)
                : datasetName;
        String filePath = "tsdb://" + cleanName;
        int columnCount = columns != null ? columns.size() : 0;
        return new Dataset(cleanName, filePath, 0, columnCount, SOURCE_TYPE, cleanName, (String) null, (java.time.OffsetDateTime) null);
    }
}
