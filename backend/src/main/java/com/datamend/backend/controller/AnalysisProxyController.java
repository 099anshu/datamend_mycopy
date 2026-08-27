package com.datamend.backend.controller;

import com.datamend.backend.dto.AnalysisRequestDto;
import com.datamend.backend.dto.DatasetRequestDto;
import com.datamend.backend.service.AnalysisProxyService;
import com.datamend.backend.service.MlServiceException;
import com.datamend.backend.service.orchestration.AnalysisOrchestrationService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/ml")
public class AnalysisProxyController {

    private final AnalysisProxyService proxyService;
    private final AnalysisOrchestrationService orchestrationService;

    public AnalysisProxyController(
            AnalysisProxyService proxyService,
            AnalysisOrchestrationService orchestrationService) {
        this.proxyService = proxyService;
        this.orchestrationService = orchestrationService;
    }

    @PostMapping("/analyze")
    public ResponseEntity<Map<String, Object>> analyze(@RequestBody AnalysisRequestDto request) {
        return call(() -> {
            DatasetRequestDto datasetRequest = new DatasetRequestDto(
                    request.datasetName(),
                    "uploads/" + request.datasetName(),
                    0,
                    request.columns().size()
            );
            UUID analysisId = orchestrationService.startAnalysis(datasetRequest, request);
            return Map.of("analysisId", analysisId.toString(), "status", "RUNNING");
        });
    }

    @PostMapping("/scores")
    public ResponseEntity<Map<String, Object>> scores(@RequestBody AnalysisRequestDto request) {
        return call(() -> proxyService.scores(request));
    }

    private ResponseEntity<Map<String, Object>> call(CallableAction action) {
        try {
            return ResponseEntity.ok(action.execute());
        } catch (MlServiceException exc) {
            HttpStatus status = exc.getStatus() != null
                    ? HttpStatus.valueOf(exc.getStatus().value())
                    : HttpStatus.BAD_GATEWAY;
            return ResponseEntity.status(status)
                    .body(Map.of("error", exc.getBody()));
        } catch (RuntimeException exc) {
            if (exc.getCause() instanceof MlServiceException mlExc) {
                HttpStatus status = mlExc.getStatus() != null
                        ? HttpStatus.valueOf(mlExc.getStatus().value())
                        : HttpStatus.BAD_GATEWAY;
                return ResponseEntity.status(status)
                        .body(Map.of("error", mlExc.getBody()));
            }
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", exc.getMessage()));
        }
    }

    @FunctionalInterface
    private interface CallableAction {
        Map<String, Object> execute();
    }
}