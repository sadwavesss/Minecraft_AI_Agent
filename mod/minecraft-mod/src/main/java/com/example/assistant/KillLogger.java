package com.example.assistant;

import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;

import java.util.LinkedHashMap;
import java.util.Map;

public final class KillLogger {
    private static BackendLogClient backendLogClient;

    private KillLogger() {
    }

    public static void init() {
        backendLogClient = BackendLogClient.fromConfig();
        ServerLivingEntityEvents.AFTER_DEATH.register(KillLogger::logKill);
    }

    private static void logKill(LivingEntity victim, DamageSource source) {
        if (backendLogClient == null) {
            return;
        }

        Entity attacker = source.getEntity();
        if (!(attacker instanceof ServerPlayer player)) {
            return;
        }

        ResourceLocation entityKey = BuiltInRegistries.ENTITY_TYPE.getKey(victim.getType());
        if (entityKey == null) {
            return;
        }

        String playerName = player.getName().getString();
        String victimName = victim.getName().getString();
        String entityId = entityKey.toString();

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("event_type", "mob_kill");

        Map<String, Object> eventData = new LinkedHashMap<>();
        eventData.put("entity_id", entityId);
        eventData.put("entity_name", victimName);
        eventData.put("count_delta", 1);
        eventData.put("killer_name", playerName);
        payload.put("event_data", eventData);

        payload.put("level", "INFO");
        payload.put("message", "mob_kill: " + playerName + " -> " + entityId);
        backendLogClient.postLog(payload);
    }
}
