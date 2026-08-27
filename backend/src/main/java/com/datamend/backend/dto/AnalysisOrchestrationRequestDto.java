package com.datamend.backend.dto;

import java.util.List;

public record AnalysisOrchestrationRequestDto(
        String analysisId,
        String datasetName,
        List<String> columns,
        String detector,
        Double threshold,
        CorruptionDto corruption,
        MissingValueHandlingDto missingValueHandling
) {}