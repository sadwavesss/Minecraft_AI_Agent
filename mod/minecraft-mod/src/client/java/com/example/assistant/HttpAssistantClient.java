package com.example.assistant;

import com.google.gson.Gson;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public final class HttpAssistantClient {
    private static final Gson GSON = new Gson();

    private final HttpClient http;
    private final AssistantConfig cfg;

    public HttpAssistantClient(AssistantConfig cfg) {
        this.cfg = cfg;
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(3))
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    private String baseUrl() {
        String url = cfg.serverUrl == null ? "" : cfg.serverUrl.trim();
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }

    public CompletableFuture<Void> postLog(Map<String, Object> payload) {
        String json = GSON.toJson(payload);
        byte[] body = json.getBytes(StandardCharsets.UTF_8);

        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl() + "/api/logs/"))
                .timeout(Duration.ofSeconds(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                .build();

        return http.sendAsync(req, HttpResponse.BodyHandlers.ofString())
                .thenAccept(resp -> {
                    int code = resp.statusCode();
                    if (code < 200 || code >= 300) {
                        String respBody = resp.body();
                        System.out.println("[AI Assistant] POST /api/logs/ failed: HTTP " + code + (respBody == null || respBody.isBlank() ? "" : (" body=" + respBody)));
                    }
                })
                .exceptionally(ex -> {
                    System.out.println("[AI Assistant] POST /api/logs/ exception: " + ex);
                    return null;
                });
    }

    public CompletableFuture<SettingsResponse> getSettings() {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl() + "/api/settings/"))
                .timeout(Duration.ofSeconds(5))
                .GET()
                .build();

        return http.sendAsync(req, HttpResponse.BodyHandlers.ofString())
                .thenApply(resp -> {
                    int code = resp.statusCode();
                    if (code < 200 || code >= 300) {
                        System.out.println("[AI Assistant] GET /api/settings/ failed: HTTP " + code);
                        return null;
                    }

                    try {
                        return GSON.fromJson(resp.body(), SettingsResponse.class);
                    } catch (Exception e) {
                        System.out.println("[AI Assistant] GET /api/settings/ parse error: " + e);
                        return null;
                    }
                })
                .exceptionally(ex -> {
                    System.out.println("[AI Assistant] GET /api/settings/ exception: " + ex);
                    return null;
                });
    }

    public CompletableFuture<AdviceResponse> getAdvice() {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl() + "/api/advice/"))
                .timeout(Duration.ofSeconds(5))
                .GET()
                .build();

        return http.sendAsync(req, HttpResponse.BodyHandlers.ofString())
                .thenApply(resp -> {
                    int code = resp.statusCode();
                    if (code < 200 || code >= 300) {
                        System.out.println("[AI Assistant] GET /api/advice/ failed: HTTP " + code);
                        return null;
                    }

                    try {
                        return GSON.fromJson(resp.body(), AdviceResponse.class);
                    } catch (Exception e) {
                        System.out.println("[AI Assistant] GET /api/advice/ parse error: " + e);
                        return null;
                    }
                })
                .exceptionally(ex -> {
                    System.out.println("[AI Assistant] GET /api/advice/ exception: " + ex);
                    return null;
                });
    }

    public static final class AdviceResponse {
        public String advice;
        public double confidence;
        public String level;
    }

    public static final class SettingsResponse {
        public int analysis_interval;
    }
}
