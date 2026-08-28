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
    public Dataset getOrCreateDataset(String sourceType, String datasetName, List<String> columns) {
        DatasetProvider matchedProvider = providers.stream()
                .filter(p -> p.supports(sourceType))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException(
                        "No dataset provider found for source: " + sourceType));

        Dataset resolved = matchedProvider.resolveDataset(datasetName, columns);
        if (resolved.getExternalId() == null) {
            return datasetRepository.save(resolved);
        }
        return datasetRepository
                .findBySourceTypeAndExternalId(resolved.getSourceType(), resolved.getExternalId())
                .orElseGet(() -> datasetRepository.save(resolved));
    }
}
