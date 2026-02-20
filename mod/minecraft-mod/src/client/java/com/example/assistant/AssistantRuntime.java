package com.example.assistant;

import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class AssistantRuntime {
    private final AssistantConfig cfg;
    private final HttpAssistantClient http;

    private int sendTickCountdown;
    private int adviceTickCountdown;

    private int settingsTickCountdown;
    private int runtimeSendIntervalTicks;

    private int hostileScanTickCountdown;

    private long localTick;
    private long lastLowHealthTick;
    private long lastHungerLowTick;
    private long lastNightTick;
    private long lastNearHostileTick;

    private boolean wasNight;

    private String lastAdviceShown;

    private boolean startupDone;

    public AssistantRuntime(AssistantConfig cfg) {
        this.cfg = cfg;
        this.http = new HttpAssistantClient(cfg);
        this.runtimeSendIntervalTicks = Math.max(1, cfg.sendIntervalTicks);
        this.sendTickCountdown = this.runtimeSendIntervalTicks;
        this.adviceTickCountdown = Math.max(1, cfg.adviceIntervalTicks);
        this.settingsTickCountdown = 1;

        this.hostileScanTickCountdown = 20;
    }

    public void onClientTick(Minecraft client) {
        if (client == null || client.player == null) {
            return;
        }

        localTick += 1;

        if (!startupDone) {
            startupDone = true;
            sendStartup(client);
            pullAdviceAndShow(client);
        }

        sendTickCountdown -= 1;
        adviceTickCountdown -= 1;
        settingsTickCountdown -= 1;
        hostileScanTickCountdown -= 1;

        if (settingsTickCountdown <= 0) {
            // refresh server settings ~ every 5 seconds
            settingsTickCountdown = 100;
            pullSettings();
        }

        maybeSendMvpEvents(client);

        if (sendTickCountdown <= 0) {
            sendTickCountdown = Math.max(1, runtimeSendIntervalTicks);
            sendState(client);
        }

        if (adviceTickCountdown <= 0) {
            adviceTickCountdown = Math.max(1, cfg.adviceIntervalTicks);
            pullAdviceAndShow(client);
        }
    }

    private void maybeSendMvpEvents(Minecraft client) {
        float health = client.player.getHealth();
        int food = client.player.getFoodData().getFoodLevel();

        // low_health (throttle ~ 10s)
        if (health <= 6.0f && (localTick - lastLowHealthTick) >= 200) {
            lastLowHealthTick = localTick;

            Map<String, Object> payload = new HashMap<>();
            payload.put("event_type", "low_health");
            Map<String, Object> eventData = new HashMap<>();
            eventData.put("health", (double) health);
            eventData.put("food", food);
            payload.put("event_data", eventData);
            payload.put("level", "WARNING");
            payload.put("message", "low_health: hp=" + health + ", food=" + food);
            payload.put("player_health", (double) health);
            http.postLog(payload);
        }

        // hunger_low (throttle ~ 15s)
        if (food <= 6 && (localTick - lastHungerLowTick) >= 300) {
            lastHungerLowTick = localTick;

            Map<String, Object> payload = new HashMap<>();
            payload.put("event_type", "hunger_low");
            Map<String, Object> eventData = new HashMap<>();
            eventData.put("food", food);
            eventData.put("health", (double) health);
            payload.put("event_data", eventData);
            payload.put("level", "WARNING");
            payload.put("message", "hunger_low: food=" + food + ", hp=" + health);
            payload.put("player_health", (double) health);
            http.postLog(payload);
        }

        // night (send on transition day->night, throttle ~ 60s)
        if (client.level != null) {
            long dayTime = client.level.getDayTime() % 24000L;
            boolean isNight = dayTime >= 13000L && dayTime <= 23000L;

            if (isNight && !wasNight && (localTick - lastNightTick) >= 1200) {
                lastNightTick = localTick;

                Map<String, Object> payload = new HashMap<>();
                payload.put("event_type", "night");
                Map<String, Object> eventData = new HashMap<>();
                eventData.put("time", (double) dayTime);
                payload.put("event_data", eventData);
                payload.put("level", "INFO");
                payload.put("message", "night: time=" + dayTime);
                http.postLog(payload);
            }

            wasNight = isNight;
        }

        // near_hostile (scan ~ once per second, throttle sending ~ 5s)
        if (client.level != null && hostileScanTickCountdown <= 0) {
            hostileScanTickCountdown = 20;

            double radius = 14.0;
            AABB box = client.player.getBoundingBox().inflate(radius);
            List<Entity> entities = client.level.getEntities(client.player, box);

            int count = 0;
            List<String> types = new ArrayList<>();
            for (Entity e : entities) {
                if (e instanceof Monster && e.isAlive()) {
                    count += 1;
                    if (types.size() < 5) {
                        types.add(String.valueOf(e.getType()));
                    }
                }
            }

            if (count > 0 && (localTick - lastNearHostileTick) >= 100) {
                lastNearHostileTick = localTick;

                Map<String, Object> payload = new HashMap<>();
                payload.put("event_type", "near_hostile");
                Map<String, Object> eventData = new HashMap<>();
                eventData.put("radius", radius);
                eventData.put("count", count);
                eventData.put("types", types);
                payload.put("event_data", eventData);
                payload.put("level", "WARNING");
                payload.put("message", "near_hostile: count=" + count + ", r=" + radius);
                http.postLog(payload);
            }
        }
    }

    private void sendStartup(Minecraft client) {
        float health = client.player.getHealth();
        int food = client.player.getFoodData().getFoodLevel();

        Map<String, Object> payload = new HashMap<>();
        payload.put("event_type", "startup");
        Map<String, Object> eventData = new HashMap<>();
        eventData.put("health", (double) health);
        eventData.put("food", food);
        payload.put("event_data", eventData);
        payload.put("level", "INFO");
        payload.put("message", "startup: connected. health=" + health + ", food=" + food);
        payload.put("player_health", (double) health);

        http.postLog(payload);
    }

    private void sendState(Minecraft client) {
        float health = client.player.getHealth();
        int food = client.player.getFoodData().getFoodLevel();

        Map<String, Object> payload = new HashMap<>();
        payload.put("event_type", "state");
        Map<String, Object> eventData = new HashMap<>();
        eventData.put("health", (double) health);
        eventData.put("food", food);
        payload.put("event_data", eventData);
        payload.put("level", health <= 6.0f ? "WARNING" : "INFO");
        payload.put("message", "state: health=" + health + ", food=" + food);
        payload.put("player_health", (double) health);

        http.postLog(payload);
    }

    private void pullAdviceAndShow(Minecraft client) {
        http.getAdvice().thenAccept(advice -> {
            if (advice == null || advice.advice == null || advice.advice.isBlank()) {
                return;
            }

            String msg = advice.advice.trim();
            if (msg.equals(lastAdviceShown)) {
                return;
            }

            lastAdviceShown = msg;

            client.execute(() -> {
                if (client.player == null) {
                    return;
                }
                client.player.displayClientMessage(Component.literal("[AI] " + msg), true);
            });
        });
    }

    private void pullSettings() {
        http.getSettings().thenAccept(settings -> {
            if (settings == null) {
                return;
            }

            int ms = settings.analysis_interval;
            if (ms < 100) {
                ms = 100;
            }
            if (ms > 60000) {
                ms = 60000;
            }

            int ticks = (int) Math.round(ms / 50.0);
            if (ticks < 1) {
                ticks = 1;
            }

            runtimeSendIntervalTicks = ticks;
        });
    }
}
