package com.example;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;

import com.example.assistant.AssistantConfig;
import com.example.assistant.AssistantRuntime;
import com.example.assistant.ConfigManager;

public class ExampleModClient implements ClientModInitializer {
	private static AssistantRuntime runtime;

	@Override
	public void onInitializeClient() {
		AssistantConfig cfg = ConfigManager.loadOrCreate();
		runtime = new AssistantRuntime(cfg);

		ClientTickEvents.END_CLIENT_TICK.register(runtime::onClientTick);
		ClientLifecycleEvents.CLIENT_STARTED.register(client -> {
			// Chat event listener will be registered separately via mixin
		});
	}

	public static AssistantRuntime getRuntime() {
		return runtime;
	}
}