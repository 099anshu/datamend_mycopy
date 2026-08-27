package com.datamend.backend.dto;

import java.util.List;

public record DatasetRequestDto(
        String name,
        String filePath,
        Integer rowCount,
        Integer columnCount
) {}