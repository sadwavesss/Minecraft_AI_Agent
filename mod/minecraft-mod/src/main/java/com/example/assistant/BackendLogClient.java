package com.example.assistant;

import com.google.gson.Gson;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Map;

public final class BackendLogClient {
    private static final Gson GSON = new Gson();
    private static final String DEFAULT_SERVER_URL = "http://127.0.0.1:8000";
    private static final String CONFIG_FILE_NAME = "ai_assistant.json";

    private final HttpClient http;
    private final String baseUrl;

    public BackendLogClient(String serverUrl) {
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(3))
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        this.baseUrl = normalizeBaseUrl(serverUrl);
    }

    public static BackendLogClient fromConfig() {
        return new BackendLogClient(loadServerUrl());
    }

    public void postLog(Map<String, Object> payload) {
        String json = GSON.toJson(payload);
        byte[] body = json.getBytes(StandardCharsets.UTF_8);

        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/logs/"))
                .timeout(Duration.ofSeconds(5))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                .build();

        http.sendAsync(req, HttpResponse.BodyHandlers.ofString())
                .thenAccept(resp -> {
                    int code = resp.statusCode();
                    if (code < 200 || code >= 300) {
                        String respBody = resp.body();
                        System.out.println("[AI Assistant] POST /api/logs/ failed: HTTP " + code
                                + (respBody == null || respBody.isBlank() ? "" : (" body=" + respBody)));
                    }
                })
                .exceptionally(ex -> {
                    System.out.println("[AI Assistant] POST /api/logs/ exception: " + ex);
                    return null;
                });
    }

    private static String loadServerUrl() {
        Path path = FabricLoader.getInstance().getConfigDir().resolve(CONFIG_FILE_NAME);
        if (!Files.exists(path)) {
            return DEFAULT_SERVER_URL;
        }

        try {
            String json = Files.readString(path, StandardCharsets.UTF_8);
            BackendConfig cfg = GSON.fromJson(json, BackendConfig.class);
            if (cfg != null && cfg.serverUrl != null && !cfg.serverUrl.isBlank()) {
                return cfg.serverUrl;
            }
        } catch (IOException | RuntimeException ex) {
            System.out.println("[AI Assistant] Failed to read backend config for kill logging: " + ex);
        }

        return DEFAULT_SERVER_URL;
    }

    private static String normalizeBaseUrl(String serverUrl) {
        String value = serverUrl == null ? "" : serverUrl.trim();
        if (value.isBlank()) {
            value = DEFAULT_SERVER_URL;
        }
        if (value.endsWith("/")) {
            value = value.substring(0, value.length() - 1);
        }
        return value;
    }

    private static final class BackendConfig {
        private String serverUrl;
    }
}
