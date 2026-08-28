package com.datamend.backend.controller;

import com.datamend.backend.dto.response.AnalysisResponseDto;
import com.datamend.backend.entity.Analysis;
import com.datamend.backend.entity.AnalysisStatus;
import com.datamend.backend.mapper.AnalysisMapper;
import com.datamend.backend.repository.AnalysisRepository;
import com.datamend.backend.repository.AnomalyRepository;
import com.datamend.backend.service.event.AnalysisEventService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/analyses")
public class AnalysisController {

    private final AnalysisRepository analysisRepository;
    private final AnomalyRepository anomalyRepository;
    private final AnalysisEventService eventService;

    public AnalysisController(
            AnalysisRepository analysisRepository,
            AnomalyRepository anomalyRepository,
            AnalysisEventService eventService) {
        this.analysisRepository = analysisRepository;
        this.anomalyRepository = anomalyRepository;
        this.eventService = eventService;
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

    @GetMapping(value = "/{id}/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamAnalysisEvents(@PathVariable String id) {
        UUID analysisId;
        try {
            analysisId = UUID.fromString(id);
        } catch (IllegalArgumentException e) {
            SseEmitter invalidEmitter = new SseEmitter(1000L);
            try {
                invalidEmitter.send(SseEmitter.event().name("error").data(Map.of("error", "Invalid UUID: " + id)));
                invalidEmitter.complete();
            } catch (IOException ignored) {}
            return invalidEmitter;
        }

        Analysis analysis = analysisRepository.findById(analysisId).orElse(null);
        if (analysis == null) {
            // Register emitter for pending async job
            return eventService.registerEmitter(analysisId);
        }

        // If already completed or failed, emit terminal state and complete
        if (analysis.getStatus() == AnalysisStatus.COMPLETED) {
            SseEmitter completedEmitter = new SseEmitter(5000L);
            var anomalies = anomalyRepository.findByAnalysisId(id);
            AnalysisResponseDto response = AnalysisMapper.toResponse(analysis, anomalies);
            try {
                completedEmitter.send(SseEmitter.event().name("completed").data(response));
                completedEmitter.complete();
            } catch (IOException ignored) {}
            return completedEmitter;
        } else if (analysis.getStatus() == AnalysisStatus.FAILED) {
            SseEmitter failedEmitter = new SseEmitter(5000L);
            try {
                failedEmitter.send(SseEmitter.event().name("failed").data(Map.of(
                        "analysisId", id.toString(),
                        "status", "FAILED",
                        "error", "Analysis execution failed"
                )));
                failedEmitter.complete();
            } catch (IOException ignored) {}
            return failedEmitter;
        }

        // Active analysis -> register emitter for real-time events
        return eventService.registerEmitter(id);
    }
}