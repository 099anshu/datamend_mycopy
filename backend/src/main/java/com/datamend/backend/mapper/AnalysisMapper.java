package com.datamend.backend.mapper;

import com.datamend.backend.dto.response.AnalysisResponseDto;
import com.datamend.backend.dto.response.AnomalyResponseDto;
import com.datamend.backend.entity.Analysis;
import com.datamend.backend.entity.Anomaly;

import java.util.List;
import java.util.stream.Collectors;

public final class AnalysisMapper {

    private AnalysisMapper() {}

    public static AnalysisResponseDto toResponse(Analysis analysis, List<Anomaly> anomalies) {
        List<AnomalyResponseDto> anomalyDtos = anomalies.stream()
                .map(AnalysisMapper::toResponse)
                .collect(Collectors.toList());
        return new AnalysisResponseDto(
                analysis.getId(),
                analysis.getDatasetId(),
                analysis.getStatus().name(),
                analysis.getDetector(),
                analysis.getStartedAt(),
                analysis.getCompletedAt(),
                anomalyDtos
        );
    }

    public static AnomalyResponseDto toResponse(Anomaly anomaly) {
        return new AnomalyResponseDto(
                anomaly.getId(),
                anomaly.getAnalysisId(),
                anomaly.getTimestamp(),
                anomaly.getColumnName(),
                anomaly.getValue(),
                anomaly.getScore(),
                anomaly.getSeverity(),
                anomaly.getCreatedAt()
        );
    }
}