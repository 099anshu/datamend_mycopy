package com.datamend.backend.controller;

import com.datamend.backend.service.MlServiceException;
import com.datamend.backend.service.dataset.DatasetProxyService;
import com.datamend.backend.service.dataset.DatasetService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class DatasetControllerTest {

    private final DatasetProxyService datasetProxyService = mock(DatasetProxyService.class);
    private final DatasetService datasetService = mock(DatasetService.class);
    private final DatasetController controller = new DatasetController(datasetProxyService, datasetService);

    private final MockMultipartFile file = new MockMultipartFile(
            "file", "series.csv", "text/csv", "date,temp\n2024-01-01T00:00:00,1.5\n".getBytes());

    @Test
    void uploadReturnsProfileAndRegistersDataset() {
        Map<String, Object> uploaded = Map.of("datasetId", "abc123", "name", "series.csv");
        when(datasetProxyService.upload(any(), eq("date"))).thenReturn(uploaded);

        ResponseEntity<Object> response = controller.upload(file, "date");

        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        assertEquals(uploaded, response.getBody());
        verify(datasetService).getOrCreateDataset("UPLOAD", "abc123", List.of());
    }

    @Test
    void mlServiceValidationErrorIsForwarded() {
        when(datasetProxyService.upload(any(), eq(null)))
                .thenThrow(new MlServiceException(HttpStatus.BAD_REQUEST, "{\"detail\":\"Unsupported file type\"}"));

        ResponseEntity<Object> response = controller.upload(file, null);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals(
                Map.of("error", "{\"detail\":\"Unsupported file type\"}"),
                response.getBody());
    }

    @Test
    void mlServiceUnreachableMapsToBadGateway() {
        when(datasetProxyService.list())
                .thenThrow(new MlServiceException("ML service is unreachable at http://localhost:8000"));

        ResponseEntity<Object> response = controller.list();

        assertEquals(HttpStatus.BAD_GATEWAY, response.getStatusCode());
    }

    @Test
    void getForwardsDatasetMetadata() {
        when(datasetProxyService.get("abc123")).thenReturn(Map.of("datasetId", "abc123"));

        ResponseEntity<Object> response = controller.get("abc123");

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(Map.of("datasetId", "abc123"), response.getBody());
    }
}
