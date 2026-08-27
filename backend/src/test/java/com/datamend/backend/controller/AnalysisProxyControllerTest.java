package com.datamend.backend.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import com.datamend.backend.dto.AnalysisRequestDto;
import com.datamend.backend.service.AnalysisProxyService;
import com.datamend.backend.service.MlServiceException;
import com.datamend.backend.service.orchestration.AnalysisOrchestrationService;

class AnalysisProxyControllerTest {

    private final AnalysisProxyService proxyService = org.mockito.Mockito.mock(AnalysisProxyService.class);
    private final AnalysisOrchestrationService orchestrationService = org.mockito.Mockito.mock(AnalysisOrchestrationService.class);
    private final AnalysisProxyController controller = new AnalysisProxyController(proxyService, orchestrationService);

    private AnalysisRequestDto request() {
        return new AnalysisRequestDto(
                "test-001",
                "ETTh1",
                List.of("HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"),
                "timercd",
                0.8,
                null,
                null);
    }

    @Test
    void analyzeForwardsRequestAndReturnsResponse() {
        when(orchestrationService.startAnalysis(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.eq(request())))
                .thenReturn(java.util.UUID.randomUUID());

        ResponseEntity<Map<String, Object>> response = controller.analyze(request());

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("RUNNING", response.getBody().get("status"));
        verify(orchestrationService).startAnalysis(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.eq(request()));
    }

    @Test
    void scoresForwardsRequestAndReturnsResponse() {
        Map<String, Object> mlResponse = Map.of("status", "COMPLETED", "scores", List.of());
        when(proxyService.scores(request())).thenReturn(mlResponse);

        ResponseEntity<Map<String, Object>> response = controller.scores(request());

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("COMPLETED", response.getBody().get("status"));
        verify(proxyService).scores(request());
    }

    @Test
    void mlServiceHttpErrorIsForwarded() {
        when(orchestrationService.startAnalysis(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.eq(request())))
                .thenThrow(new RuntimeException(
                        new MlServiceException(HttpStatus.BAD_REQUEST, "{\"detail\":\"bad strategy\"}")));

        ResponseEntity<Map<String, Object>> response = controller.analyze(request());

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals("{\"detail\":\"bad strategy\"}", response.getBody().get("error"));
    }

    @Test
    void mlServiceUnreachableMapsToBadGateway() {
        when(orchestrationService.startAnalysis(org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.eq(request())))
                .thenThrow(new RuntimeException(
                        new MlServiceException("ML service is unreachable at http://localhost:8000")));

        ResponseEntity<Map<String, Object>> response = controller.analyze(request());

        assertEquals(HttpStatus.BAD_GATEWAY, response.getStatusCode());
        assertEquals(
                "ML service is unreachable at http://localhost:8000",
                response.getBody().get("error"));
    }
}