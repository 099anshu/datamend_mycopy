package com.datamend.backend.service.orchestration;

import com.datamend.backend.dto.AnalysisOrchestrationRequestDto;
import com.datamend.backend.dto.AnalysisRequestDto;
import com.datamend.backend.dto.DatasetRequestDto;
import com.datamend.backend.entity.Analysis;
import com.datamend.backend.entity.AnalysisStatus;
import com.datamend.backend.entity.Anomaly;
import com.datamend.backend.entity.Dataset;
import com.datamend.backend.repository.AnalysisRepository;
import com.datamend.backend.repository.AnomalyRepository;
import com.datamend.backend.repository.DatasetRepository;
import com.datamend.backend.service.AnalysisProxyService;
import com.datamend.backend.service.MlServiceException;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Service
public class AnalysisOrchestrationService {

    private final DatasetRepository datasetRepository;
    private final AnalysisRepository analysisRepository;
    private final AnomalyRepository anomalyRepository;
    private final AnalysisProxyService proxyService;

    public AnalysisOrchestrationService(
            DatasetRepository datasetRepository,
            AnalysisRepository analysisRepository,
            AnomalyRepository anomalyRepository,
            AnalysisProxyService proxyService) {
        this.datasetRepository = datasetRepository;
        this.analysisRepository = analysisRepository;
        this.anomalyRepository = anomalyRepository;
        this.proxyService = proxyService;
    }

    @Transactional
    public UUID startAnalysis(DatasetRequestDto datasetRequest, AnalysisRequestDto mlRequest) {
        Dataset dataset = new Dataset(
                datasetRequest.name(),
                datasetRequest.filePath(),
                datasetRequest.rowCount(),
                datasetRequest.columnCount()
        );
        dataset = datasetRepository.save(dataset);

        Analysis analysis = new Analysis(dataset.getId(), AnalysisStatus.RUNNING, mlRequest.detector());
        analysis.setStartedAt(OffsetDateTime.now());
        Analysis savedAnalysis = analysisRepository.save(analysis);

        CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> mlResponse = proxyService.analyze(mlRequest);
                completeAnalysis(savedAnalysis.getId(), mlResponse);
                return mlResponse;
            } catch (MlServiceException e) {
                failAnalysis(savedAnalysis.getId(), e.getMessage());
                throw new RuntimeException(e);
            }
        });

        return savedAnalysis.getId();
    }

    @Transactional
    public void completeAnalysis(UUID analysisId, Map<String, Object> mlResponse) {
        Analysis analysis = analysisRepository.findById(analysisId)
                .orElseThrow(() -> new IllegalArgumentException("Analysis not found: " + analysisId));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> anomalyList = (List<Map<String, Object>>) mlResponse.get("anomalies");

        if (anomalyList != null && !anomalyList.isEmpty()) {
            List<Anomaly> anomalies = anomalyList.stream()
                    .map(this::mapToAnomaly)
                    .peek(a -> a.setAnalysisId(analysisId))
                    .toList();
            anomalyRepository.saveAll(anomalies);
        }

        analysis.setStatus(AnalysisStatus.COMPLETED);
        analysis.setCompletedAt(OffsetDateTime.now());
        analysisRepository.save(analysis);
    }

    @Transactional
    public void failAnalysis(UUID analysisId, String errorMessage) {
        Analysis analysis = analysisRepository.findById(analysisId)
                .orElseThrow(() -> new IllegalArgumentException("Analysis not found: " + analysisId));

        analysis.setStatus(AnalysisStatus.FAILED);
        analysis.setCompletedAt(OffsetDateTime.now());
        analysisRepository.save(analysis);
    }

    private Anomaly mapToAnomaly(Map<String, Object> anomalyMap) {
        OffsetDateTime timestamp = OffsetDateTime.parse((String) anomalyMap.get("timestamp"));
        String columnName = (String) anomalyMap.get("column_name");
        Double value = anomalyMap.get("value") != null ? ((Number) anomalyMap.get("value")).doubleValue() : null;
        Double score = anomalyMap.get("score") != null ? ((Number) anomalyMap.get("score")).doubleValue() : null;
        String severity = (String) anomalyMap.get("severity");
        return new Anomaly(null, timestamp, columnName, value, score, severity);
    }
}