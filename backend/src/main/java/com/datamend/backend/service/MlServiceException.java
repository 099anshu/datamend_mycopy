package com.datamend.backend.service;

import org.springframework.http.HttpStatusCode;

public class MlServiceException extends RuntimeException {

    private final HttpStatusCode status;
    private final String body;

    public MlServiceException(HttpStatusCode status, String body) {
        super("ML service returned " + status + ": " + body);
        this.status = status;
        this.body = body;
    }

    public MlServiceException(String message) {
        super(message);
        this.status = null;
        this.body = message;
    }

    public HttpStatusCode getStatus() {
        return status;
    }

    public String getBody() {
        return body;
    }
}