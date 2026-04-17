import os
import time
import pygame
import asyncio
import edge_tts
import json

pygame.mixer.init()

async def _generate_audio(text, filename, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def speak(text):
    if not text: return
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            current_voice = "uk-UA-OstapNeural" if "Ostap" in cfg.get("voice", "") else "uk-UA-PolinaNeural"
    except: current_voice = "uk-UA-PolinaNeural"

    try:
        filename = f"voice_temp_{int(time.time())}.mp3"
        asyncio.run(_generate_audio(text, filename, current_voice))
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        os.remove(filename)
    except Exception as e:
        print(f"❌ [TTS Помилка]: {e}")