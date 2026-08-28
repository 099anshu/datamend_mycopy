package com.datamend.backend.controller;

import com.datamend.backend.service.MlServiceException;
import com.datamend.backend.service.dataset.DatasetProxyService;
import com.datamend.backend.service.dataset.DatasetService;
import com.datamend.backend.service.dataset.UploadedDatasetProvider;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

@RestController
@RequestMapping("/api/v1/datasets")
public class DatasetController {

    private final DatasetProxyService datasetProxyService;
    private final DatasetService datasetService;

    public DatasetController(DatasetProxyService datasetProxyService, DatasetService datasetService) {
        this.datasetProxyService = datasetProxyService;
        this.datasetService = datasetService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Object> upload(
            @RequestPart("file") MultipartFile file,
            @RequestParam(value = "timestampColumn", required = false) String timestampColumn) {
        return call(HttpStatus.CREATED, () -> {
            Map<String, Object> uploaded = datasetProxyService.upload(file, timestampColumn);
            String datasetId = (String) uploaded.get("datasetId");
            // Register the upload so analyses can reference it without a second round trip.
            datasetService.getOrCreateDataset(UploadedDatasetProvider.SOURCE_TYPE, datasetId, List.of());
            return uploaded;
        });
    }

    @GetMapping
    public ResponseEntity<Object> list() {
        return call(HttpStatus.OK, datasetProxyService::list);
    }

    @GetMapping("/sources/tsdb")
    public ResponseEntity<Object> listTsdbDatasets() {
        return call(HttpStatus.OK, datasetProxyService::listTsdbDatasets);
    }

    @GetMapping("/{datasetId}")
    public ResponseEntity<Object> get(@PathVariable String datasetId) {
        return call(HttpStatus.OK, () -> datasetProxyService.get(datasetId));
    }

    private ResponseEntity<Object> call(HttpStatus successStatus, Supplier<Object> action) {
        try {
            return ResponseEntity.status(successStatus).body(action.get());
        } catch (MlServiceException exc) {
            HttpStatus status = exc.getStatus() != null
                    ? HttpStatus.valueOf(exc.getStatus().value())
                    : HttpStatus.BAD_GATEWAY;
            return ResponseEntity.status(status).body(Map.of("error", exc.getBody()));
        } catch (IllegalArgumentException exc) {
            return ResponseEntity.badRequest().body(Map.of("error", exc.getMessage()));
        }
    }
}
