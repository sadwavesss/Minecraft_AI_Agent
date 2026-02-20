package com.example.assistant;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class ConfigManager {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String FILE_NAME = "ai_assistant.json";

    private ConfigManager() {
    }

    public static Path configPath() {
        return FabricLoader.getInstance().getConfigDir().resolve(FILE_NAME);
    }

    public static AssistantConfig loadOrCreate() {
        Path path = configPath();

        if (Files.exists(path)) {
            try {
                String json = Files.readString(path, StandardCharsets.UTF_8);
                AssistantConfig cfg = GSON.fromJson(json, AssistantConfig.class);
                if (cfg != null) {
                    return cfg;
                }
            } catch (Exception ignored) {
            }
        }

        AssistantConfig cfg = new AssistantConfig();
        save(cfg);
        return cfg;
    }

    public static void save(AssistantConfig cfg) {
        Path path = configPath();
        try {
            Files.createDirectories(path.getParent());
            Files.writeString(path, GSON.toJson(cfg), StandardCharsets.UTF_8);
        } catch (IOException ignored) {
        }
    }
}
