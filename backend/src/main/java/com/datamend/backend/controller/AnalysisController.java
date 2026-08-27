package com.datamend.backend.controller;

import com.datamend.backend.dto.response.AnalysisResponseDto;
import com.datamend.backend.entity.Analysis;
import com.datamend.backend.entity.Anomaly;
import com.datamend.backend.mapper.AnalysisMapper;
import com.datamend.backend.repository.AnalysisRepository;
import com.datamend.backend.repository.AnomalyRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/analyses")
public class AnalysisController {

    private final AnalysisRepository analysisRepository;
    private final AnomalyRepository anomalyRepository;

    public AnalysisController(AnalysisRepository analysisRepository, AnomalyRepository anomalyRepository) {
        this.analysisRepository = analysisRepository;
        this.anomalyRepository = anomalyRepository;
    }

    @GetMapping("/{id}")
    public ResponseEntity<AnalysisResponseDto> getAnalysis(@PathVariable UUID id) {
        Analysis analysis = analysisRepository.findById(id).orElse(null);
        if (analysis == null) {
            return ResponseEntity.notFound().build();
        }
        var anomalies = anomalyRepository.findByAnalysisId(id);
        AnalysisResponseDto response = AnalysisMapper.toResponse(analysis, anomalies);
        return ResponseEntity.ok(response);
    }
}