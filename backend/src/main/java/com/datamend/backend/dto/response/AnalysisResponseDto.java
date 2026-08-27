package com.datamend.backend.dto.response;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

public record AnalysisResponseDto(
        UUID id,
        UUID datasetId,
        String status,
        String detector,
        OffsetDateTime startedAt,
        OffsetDateTime completedAt,
        List<AnomalyResponseDto> anomalies
) {}