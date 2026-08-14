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

class AnalysisProxyControllerTest {

    private final AnalysisProxyService proxyService = org.mockito.Mockito.mock(AnalysisProxyService.class);
    private final AnalysisProxyController controller = new AnalysisProxyController(proxyService);

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
        Map<String, Object> mlResponse = Map.of("status", "COMPLETED", "anomalies", List.of());
        when(proxyService.analyze(request())).thenReturn(mlResponse);

        ResponseEntity<Map<String, Object>> response = controller.analyze(request());

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("COMPLETED", response.getBody().get("status"));
        verify(proxyService).analyze(request());
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
        when(proxyService.analyze(request())).thenThrow(
                new MlServiceException(HttpStatus.BAD_REQUEST, "{\"detail\":\"bad strategy\"}"));

        ResponseEntity<Map<String, Object>> response = controller.analyze(request());

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals("{\"detail\":\"bad strategy\"}", response.getBody().get("error"));
    }

    @Test
    void mlServiceUnreachableMapsToBadGateway() {
        when(proxyService.analyze(request())).thenThrow(
                new MlServiceException("ML service is unreachable at http://localhost:8000"));

        ResponseEntity<Map<String, Object>> response = controller.analyze(request());

        assertEquals(HttpStatus.BAD_GATEWAY, response.getStatusCode());
        assertEquals(
                "ML service is unreachable at http://localhost:8000",
                response.getBody().get("error"));
    }
}