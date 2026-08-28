package com.datamend.backend.service.dataset;

import com.datamend.backend.service.MlServiceException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Passthrough to the ml-service dataset endpoints, which own upload storage and profiling.
 */
@Service
public class DatasetProxyService {

    private final RestClient restClient;
    private final String baseUrl;

    public DatasetProxyService(
            @Value("${ml-service.base-url}") String baseUrl,
            RestClient.Builder builder) {
        this.baseUrl = baseUrl;
        this.restClient = builder.baseUrl(baseUrl).build();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> upload(MultipartFile file, String timestampColumn) {
        MultiValueMap<String, Object> form = new LinkedMultiValueMap<>();
        form.add("file", asResource(file));
        if (timestampColumn != null && !timestampColumn.isBlank()) {
            form.add("timestampColumn", timestampColumn);
        }
        return call(() -> restClient.post()
                .uri("/api/v1/datasets")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(form)
                .retrieve()
                .body(Map.class));
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> list() {
        return call(() -> restClient.get()
                .uri("/api/v1/datasets")
                .retrieve()
                .body(List.class));
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> get(String datasetId) {
        return call(() -> restClient.get()
                .uri("/api/v1/datasets/{id}", datasetId)
                .retrieve()
                .body(Map.class));
    }

    @SuppressWarnings("unchecked")
    public List<String> listTsdbDatasets() {
        return call(() -> restClient.get()
                .uri("/api/v1/datasets/sources/tsdb")
                .retrieve()
                .body(List.class));
    }

    private ByteArrayResource asResource(MultipartFile file) {
        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException exc) {
            throw new IllegalArgumentException("Could not read uploaded file: " + exc.getMessage(), exc);
        }
        return new ByteArrayResource(bytes) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        };
    }

    private <T> T call(java.util.function.Supplier<T> action) {
        try {
            return action.get();
        } catch (RestClientResponseException exc) {
            throw new MlServiceException(exc.getStatusCode(), exc.getResponseBodyAsString());
        } catch (ResourceAccessException exc) {
            throw new MlServiceException(
                    "ML service is unreachable at " + baseUrl
                            + ". Is the ml-service running on port 8000?");
        }
    }
}
