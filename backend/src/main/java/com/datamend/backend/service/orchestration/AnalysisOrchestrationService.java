package com.datamend.backend.service.orchestration;

import com.datamend.backend.dto.AnalysisRequestDto;
import com.datamend.backend.dto.DatasetRequestDto;
import com.datamend.backend.dto.response.AnalysisResponseDto;
import com.datamend.backend.entity.Analysis;
import com.datamend.backend.entity.AnalysisStatus;
import com.datamend.backend.entity.Anomaly;
import com.datamend.backend.entity.Dataset;
import com.datamend.backend.mapper.AnalysisMapper;
import com.datamend.backend.repository.AnalysisRepository;
import com.datamend.backend.repository.AnomalyRepository;
import com.datamend.backend.service.AnalysisProxyService;
import com.datamend.backend.service.MlServiceException;
import com.datamend.backend.service.dataset.DatasetService;
import com.datamend.backend.service.event.AnalysisEventService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Service
public class AnalysisOrchestrationService {

    private static final Logger log = LoggerFactory.getLogger(AnalysisOrchestrationService.class);

    private final DatasetService datasetService;
    private final AnalysisRepository analysisRepository;
    private final AnomalyRepository anomalyRepository;
    private final AnalysisProxyService proxyService;
    private final AnalysisEventService eventService;

    public AnalysisOrchestrationService(
            DatasetService datasetService,
            AnalysisRepository analysisRepository,
            AnomalyRepository anomalyRepository,
            AnalysisProxyService proxyService,
            AnalysisEventService eventService) {
        this.datasetService = datasetService;
        this.analysisRepository = analysisRepository;
        this.anomalyRepository = anomalyRepository;
        this.proxyService = proxyService;
        this.eventService = eventService;
    }

    @Transactional
    public UUID startAnalysis(AnalysisRequestDto mlRequest) {
        Dataset dataset = datasetService.getOrCreateDataset(
                mlRequest.source(), mlRequest.datasetName(), mlRequest.columns());

        Analysis analysis = new Analysis(dataset.getId(), AnalysisStatus.RUNNING, mlRequest.detector());
        analysis.setStartedAt(OffsetDateTime.now());
        Analysis savedAnalysis = analysisRepository.save(analysis);
        UUID analysisId = savedAnalysis.getId();

        eventService.emitStatus(analysisId, AnalysisStatus.RUNNING);

        CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> mlResponse = proxyService.analyze(mlRequest);
                completeAnalysis(analysisId, mlResponse);
                return mlResponse;
            } catch (MlServiceException e) {
                log.error("ML service error during analysis {}", analysisId, e);
                failAnalysis(analysisId, e.getMessage());
                throw new RuntimeException(e);
            } catch (Exception e) {
                log.error("Unexpected error during analysis {}", analysisId, e);
                failAnalysis(analysisId, e.getMessage());
                throw new RuntimeException(e);
            }
        });

        return analysisId;
    }

    @Deprecated
    @Transactional
    public UUID startAnalysis(DatasetRequestDto datasetRequest, AnalysisRequestDto mlRequest) {
        return startAnalysis(mlRequest);
    }

    @Transactional
    public void completeAnalysis(UUID analysisId, Map<String, Object> mlResponse) {
        Analysis analysis = analysisRepository.findById(analysisId)
                .orElseThrow(() -> new IllegalArgumentException("Analysis not found: " + analysisId));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> anomalyList = (List<Map<String, Object>>) mlResponse.get("anomalies");

        List<Anomaly> savedAnomalies = new ArrayList<>();
        if (anomalyList != null && !anomalyList.isEmpty()) {
            List<Anomaly> anomalies = anomalyList.stream()
                    .map(this::mapToAnomaly)
                    .peek(a -> a.setAnalysisId(analysisId))
                    .toList();
            savedAnomalies = anomalyRepository.saveAll(anomalies);
        }

        analysis.setStatus(AnalysisStatus.COMPLETED);
        analysis.setCompletedAt(OffsetDateTime.now());
        Analysis updatedAnalysis = analysisRepository.save(analysis);

        AnalysisResponseDto responseDto = AnalysisMapper.toResponse(updatedAnalysis, savedAnomalies);
        eventService.emitCompleted(analysisId, responseDto);
    }

    @Transactional
    public void failAnalysis(UUID analysisId, String errorMessage) {
        Analysis analysis = analysisRepository.findById(analysisId)
                .orElseThrow(() -> new IllegalArgumentException("Analysis not found: " + analysisId));

        analysis.setStatus(AnalysisStatus.FAILED);
        analysis.setCompletedAt(OffsetDateTime.now());
        analysisRepository.save(analysis);

        eventService.emitFailed(analysisId, errorMessage);
    }

    private Anomaly mapToAnomaly(Map<String, Object> anomalyMap) {
        String rawTimestamp = (String) anomalyMap.get("timestamp");
        OffsetDateTime timestamp = OffsetDateTime.parse(rawTimestamp);

        // Support both "column" (FastAPI schema) and "column_name" (legacy DB convention)
        String columnName = (String) anomalyMap.get("column");
        if (columnName == null) {
            columnName = (String) anomalyMap.get("column_name");
        }
        if (columnName == null) {
            columnName = "unknown";
        }

        Double value = anomalyMap.get("value") != null ? ((Number) anomalyMap.get("value")).doubleValue() : null;
        Double score = anomalyMap.get("score") != null ? ((Number) anomalyMap.get("score")).doubleValue() : null;
        String severity = (String) anomalyMap.get("severity");
        if (severity == null) {
            severity = score != null && score > 0.9 ? "HIGH" : (score != null && score > 0.6 ? "MEDIUM" : "LOW");
        }
        return new Anomaly(null, timestamp, columnName, value, score, severity);
    }
}