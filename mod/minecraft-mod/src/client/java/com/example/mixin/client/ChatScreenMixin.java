package com.example.mixin.client;

import net.minecraft.client.gui.screens.ChatScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import com.example.ExampleModClient;

@Mixin(ChatScreen.class)
public class ChatScreenMixin {
    // Try to inject at return point of onClose/init to detect when user sends message
    @Inject(at = @At("HEAD"), method = "tick")
    private void onTick(CallbackInfo info) {
        // no-op: tick injection retained for mixin compatibility
    }
}
