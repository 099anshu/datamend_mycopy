package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@Order(Ordered.LOWEST_PRECEDENCE)
public class TsdbDatasetProvider implements DatasetProvider {

    @Override
    public String getSourceType() {
        return "TSDB";
    }

    @Override
    public boolean supports(String datasetName) {
        return datasetName != null && !datasetName.isBlank();
    }

    @Override
    public Dataset resolveDataset(String datasetName, List<String> columns) {
        String cleanName = datasetName.startsWith("tsdb://") 
                ? datasetName.substring(7) 
                : datasetName;
        String filePath = "tsdb://" + cleanName;
        int columnCount = columns != null ? columns.size() : 0;
        return new Dataset(cleanName, filePath, 0, columnCount);
    }
}
