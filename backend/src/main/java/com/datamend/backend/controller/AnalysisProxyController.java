package com.datamend.backend.controller;

import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.datamend.backend.dto.AnalysisRequestDto;
import com.datamend.backend.service.AnalysisProxyService;
import com.datamend.backend.service.MlServiceException;

@RestController
@RequestMapping("/api/v1/ml")
public class AnalysisProxyController {

    private final AnalysisProxyService proxyService;

    public AnalysisProxyController(AnalysisProxyService proxyService) {
        this.proxyService = proxyService;
    }

    @PostMapping("/analyze")
    public ResponseEntity<Map<String, Object>> analyze(@RequestBody AnalysisRequestDto request) {
        return call(() -> proxyService.analyze(request));
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
        }
    }

    @FunctionalInterface
    private interface CallableAction {
        Map<String, Object> execute();
    }
}