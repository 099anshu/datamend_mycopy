package com.datamend.backend.dto;

import java.util.Map;

public record CorruptionDto(
        boolean enabled,
        String method,
        Map<String, Object> params) {
}