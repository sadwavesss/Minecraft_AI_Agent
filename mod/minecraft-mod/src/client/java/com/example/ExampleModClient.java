package com.example;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;

import com.example.assistant.AssistantConfig;
import com.example.assistant.AssistantRuntime;
import com.example.assistant.ConfigManager;

public class ExampleModClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		AssistantConfig cfg = ConfigManager.loadOrCreate();
		AssistantRuntime runtime = new AssistantRuntime(cfg);

		ClientTickEvents.END_CLIENT_TICK.register(runtime::onClientTick);
	}
}