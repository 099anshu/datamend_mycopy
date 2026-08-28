package com.datamend.backend.dto;

import java.util.List;

public record AnalysisRequestDto(
        String analysisId,
        String datasetName,
        List<String> columns,
        String detector,
        String source,
        String timestampColumn,
        Double threshold,
        CorruptionDto corruption,
        MissingValueHandlingDto missingValueHandling) {
}