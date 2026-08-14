package com.datamend.backend.service;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import com.datamend.backend.dto.AnalysisRequestDto;

import com.sun.net.httpserver.HttpServer;

class RestClientBodyProbeTest {

    @Test
    void restClientSendsDtoBody() throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        final StringBuilder received = new StringBuilder();
        server.createContext("/api/v1/analyze", exchange -> {
            byte[] body = exchange.getRequestBody().readAllBytes();
            received.append(new String(body, StandardCharsets.UTF_8));
            byte[] response = "{\"ok\":true}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, response.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(response);
            }
        });
        server.start();
        try {
            String baseUrl = "http://localhost:" + server.getAddress().getPort();
            RestClient client = RestClient.builder().baseUrl(baseUrl).build();

            AnalysisRequestDto request = new AnalysisRequestDto(
                    "t", "ETTh1", List.of("HUFL"), "timercd", 0.8, null, null);

            client.post()
                    .uri("/api/v1/analyze")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(request)
                    .retrieve()
                    .body(Map.class);

            assertEquals("{\"analysisId\":\"t\",\"datasetName\":\"ETTh1\",\"columns\":[\"HUFL\"],\"detector\":\"timercd\",\"threshold\":0.8,\"corruption\":null,\"missingValueHandling\":null}", received.toString());
        } finally {
            server.stop(0);
        }
    }
}
