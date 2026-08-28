package com.datamend.backend.service.dataset;

import com.datamend.backend.entity.Dataset;
import com.datamend.backend.repository.DatasetRepository;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class DatasetServiceTest {

    private final DatasetRepository datasetRepository = mock(DatasetRepository.class);
    private final DatasetProxyService datasetProxyService = mock(DatasetProxyService.class);
    private final UploadedDatasetProvider uploadedProvider =
            new UploadedDatasetProvider(datasetProxyService, new ObjectMapper());
    private final TsdbDatasetProvider tsdbProvider = new TsdbDatasetProvider();
    private final DatasetService datasetService =
            new DatasetService(List.of(uploadedProvider, tsdbProvider), datasetRepository);

    private void stubUploadMetadata() {
        when(datasetProxyService.get("abc123")).thenReturn(Map.of(
                "datasetId", "abc123",
                "name", "series.csv",
                "uploadedAt", "2024-01-01T00:00:00+00:00",
                "profile", Map.of(
                        "rowCount", 120,
                        "columnCount", 4,
                        "timestampColumn", "date")));
    }

    @Test
    void uploadSourceResolvesThroughUploadedProvider() {
        stubUploadMetadata();
        when(datasetRepository.findBySourceTypeAndExternalId("UPLOAD", "abc123")).thenReturn(Optional.empty());
        when(datasetRepository.save(any(Dataset.class))).thenAnswer(inv -> inv.getArgument(0));

        Dataset dataset = datasetService.getOrCreateDataset("upload", "abc123", List.of("temp"));

        assertEquals("UPLOAD", dataset.getSourceType());
        assertEquals("series.csv", dataset.getName());
        assertEquals("upload://abc123", dataset.getFilePath());
        assertEquals(120, dataset.getRowCount());
        assertEquals(4, dataset.getColumnCount());
        assertEquals(
                Map.of("rowCount", 120, "columnCount", 4, "timestampColumn", "date"),
                new ObjectMapper().readValue(dataset.getProfile(), Map.class));
    }

    @Test
    void alreadyRegisteredUploadIsReusedInsteadOfDuplicated() {
        stubUploadMetadata();
        Dataset existing = new Dataset("series.csv", "upload://abc123", 120, 4, "UPLOAD", "abc123", null, null);
        when(datasetRepository.findBySourceTypeAndExternalId("UPLOAD", "abc123")).thenReturn(Optional.of(existing));

        Dataset dataset = datasetService.getOrCreateDataset("upload", "abc123", List.of("temp"));

        assertSame(existing, dataset);
        verify(datasetRepository, never()).save(any(Dataset.class));
    }

    @Test
    void missingSourceFallsBackToTsdb() {
        when(datasetRepository.findBySourceTypeAndExternalId("TSDB", "ETTh1")).thenReturn(Optional.empty());
        when(datasetRepository.save(any(Dataset.class))).thenAnswer(inv -> inv.getArgument(0));

        Dataset dataset = datasetService.getOrCreateDataset(null, "ETTh1", List.of("OT"));

        assertEquals("TSDB", dataset.getSourceType());
        assertEquals("tsdb://ETTh1", dataset.getFilePath());
    }

    @Test
    void unknownSourceIsRejected() {
        IllegalArgumentException exc = assertThrows(
                IllegalArgumentException.class,
                () -> datasetService.getOrCreateDataset("s3", "bucket/key", List.of()));

        assertEquals("No dataset provider found for source: s3", exc.getMessage());
    }
}
