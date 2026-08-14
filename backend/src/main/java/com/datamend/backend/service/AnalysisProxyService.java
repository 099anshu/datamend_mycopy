package com.datamend.backend.service;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import com.datamend.backend.dto.AnalysisRequestDto;

@Service
public class AnalysisProxyService {

    private final RestClient restClient;
    private final String baseUrl;

    public AnalysisProxyService(
            @Value("${ml-service.base-url}") String baseUrl,
            RestClient.Builder builder) {
        this.baseUrl = baseUrl;
        this.restClient = builder.baseUrl(baseUrl).build();
    }

    public Map<String, Object> analyze(AnalysisRequestDto request) {
        return post("/api/v1/analyze", request);
    }

    public Map<String, Object> scores(AnalysisRequestDto request) {
        return post("/api/v1/scores", request);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, AnalysisRequestDto request) {
        try {
            return restClient.post()
                    .uri(path)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(request)
                    .retrieve()
                    .body(Map.class);
        } catch (RestClientResponseException exc) {
            throw new MlServiceException(exc.getStatusCode(), exc.getResponseBodyAsString());
        } catch (ResourceAccessException exc) {
            throw new MlServiceException(
                    "ML service is unreachable at " + baseUrl
                            + ". Is the ml-service running on port 8000?");
        }
    }
}