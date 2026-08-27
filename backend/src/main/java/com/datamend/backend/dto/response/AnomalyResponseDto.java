package com.datamend.backend.dto.response;

import java.time.OffsetDateTime;
import java.util.UUID;

public record AnomalyResponseDto(
        UUID id,
        UUID analysisId,
        OffsetDateTime timestamp,
        String columnName,
        Double value,
        Double score,
        String severity,
        OffsetDateTime createdAt
) {}