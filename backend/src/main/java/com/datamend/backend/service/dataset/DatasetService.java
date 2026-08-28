package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;
import com.datamend.backend.repository.DatasetRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Service layer coordinating modular dataset resolution and persistence.
 */
@Service
public class DatasetService {

    private final List<DatasetProvider> providers;
    private final DatasetRepository datasetRepository;

    public DatasetService(List<DatasetProvider> providers, DatasetRepository datasetRepository) {
        this.providers = providers;
        this.datasetRepository = datasetRepository;
    }

    @Transactional
    public Dataset getOrCreateDataset(String datasetName, List<String> columns) {
        DatasetProvider matchedProvider = providers.stream()
                .filter(p -> p.supports(datasetName))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No dataset provider found for dataset: " + datasetName));

        Dataset dataset = matchedProvider.resolveDataset(datasetName, columns);
        return datasetRepository.save(dataset);
    }
}
