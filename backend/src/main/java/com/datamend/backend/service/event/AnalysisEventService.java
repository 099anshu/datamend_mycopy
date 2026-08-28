package com.datamend.backend.service.event;

import com.datamend.backend.dto.response.AnalysisResponseDto;
import com.datamend.backend.entity.AnalysisStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class AnalysisEventService {

    private static final Logger log = LoggerFactory.getLogger(AnalysisEventService.class);
    private static final long SSE_TIMEOUT_MS = 5 * 60 * 1000L; // 5 minutes

    private final Map<UUID, List<SseEmitter>> emittersByAnalysis = new ConcurrentHashMap<>();

    public SseEmitter registerEmitter(UUID analysisId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT_MS);
        emittersByAnalysis.computeIfAbsent(analysisId, k -> new CopyOnWriteArrayList<>()).add(emitter);

        Runnable cleanup = () -> removeEmitter(analysisId, emitter);
        emitter.onCompletion(cleanup);
        emitter.onTimeout(cleanup);
        emitter.onError(e -> cleanup.run());

        // Send initial connect ping
        try {
            emitter.send(SseEmitter.event()
                    .name("connected")
                    .data(Map.of("analysisId", analysisId.toString(), "message", "SSE stream established")));
        } catch (IOException e) {
            log.warn("Failed to send initial SSE connection ping for analysis {}", analysisId, e);
            cleanup.run();
        }

        return emitter;
    }

    public void emitStatus(UUID analysisId, AnalysisStatus status) {
        List<SseEmitter> emitters = emittersByAnalysis.get(analysisId);
        if (emitters == null || emitters.isEmpty()) {
            return;
        }

        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("status")
                        .data(Map.of("analysisId", analysisId.toString(), "status", status.name())));
            } catch (Exception e) {
                log.debug("Failed sending status event to emitter for analysis {}", analysisId, e);
                removeEmitter(analysisId, emitter);
            }
        }
    }

    public void emitCompleted(UUID analysisId, AnalysisResponseDto response) {
        List<SseEmitter> emitters = emittersByAnalysis.remove(analysisId);
        if (emitters == null || emitters.isEmpty()) {
            return;
        }

        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("completed")
                        .data(response));
                emitter.complete();
            } catch (Exception e) {
                log.debug("Failed sending completed event to emitter for analysis {}", analysisId, e);
                removeEmitter(analysisId, emitter);
            }
        }
    }

    public void emitFailed(UUID analysisId, String errorMessage) {
        List<SseEmitter> emitters = emittersByAnalysis.remove(analysisId);
        if (emitters == null || emitters.isEmpty()) {
            return;
        }

        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name("failed")
                        .data(Map.of(
                                "analysisId", analysisId.toString(),
                                "status", AnalysisStatus.FAILED.name(),
                                "error", errorMessage != null ? errorMessage : "Analysis failed"
                        )));
                emitter.complete();
            } catch (Exception e) {
                log.debug("Failed sending failed event to emitter for analysis {}", analysisId, e);
                removeEmitter(analysisId, emitter);
            }
        }
    }

    private void removeEmitter(UUID analysisId, SseEmitter emitter) {
        List<SseEmitter> emitters = emittersByAnalysis.get(analysisId);
        if (emitters != null) {
            emitters.remove(emitter);
            if (emitters.isEmpty()) {
                emittersByAnalysis.remove(analysisId, emitters);
            }
        }
    }
}
