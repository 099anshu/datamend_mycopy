package com.datamend.backend.dto;

public record DatasetRequestDto(
        String name,
        String filePath,
        Integer rowCount,
        Integer columnCount
) {}