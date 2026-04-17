import telebot
from telebot import types
import json
import time
import os
import speech_recognition as sr # Повернули Google
from pydub import AudioSegment
from modules.controller import execute_system_command, get_system_status
from modules.ai_brain import generate_response
import modules.surveillance as surv

def start_telegram_bot(status_callback):
    print("[Telegram] Бот на старті. Чекаю токен...")
    
    while True:
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            token = cfg.get("telegram_token", "").strip()
            
            if not token:
                time.sleep(5); continue

            bot = telebot.TeleBot(token)
            recognizer = sr.Recognizer() # Ініціалізуємо розпізнавач

            def get_main_keyboard():
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton('📊 Стан ПК'), types.KeyboardButton('📸 Фото'), types.KeyboardButton('🖼️ Скріншот'))
                markup.add(types.KeyboardButton('🛡 Охорона'), types.KeyboardButton('❓ Допомога'))
                return markup

            def security_alert(msg):
                try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        chat_id = json.load(f).get("telegram_chat_id", "").strip()
                    if chat_id:
                        if msg.startswith("file:"):
                            with open(msg.replace("file:", ""), "rb") as audio:
                                bot.send_audio(chat_id, audio)
                        else:
                            bot.send_message(chat_id, msg)
                except Exception as e: print("Помилка alert:", e)
            
            surv.SECURITY_CALLBACK = security_alert

            def check_auth(message):
                with open('config.json', 'r', encoding='utf-8') as f:
                    auth_id = json.load(f).get("telegram_chat_id", "").strip()
                if auth_id and str(message.chat.id) != auth_id:
                    bot.reply_to(message, "⛔ Доступ заборонено.")
                    return False
                return True

            @bot.message_handler(content_types=['voice'])
            def handle_voice(message):
                if not check_auth(message): return
                try:
                    bot.send_chat_action(message.chat.id, 'record_voice')
                    file_info = bot.get_file(message.voice.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    
                    with open("tg_voice.ogg", 'wb') as f:
                        f.write(downloaded_file)
                    
                    # Конвертація через FFmpeg
                    audio = AudioSegment.from_file("tg_voice.ogg", format="ogg")
                    audio.export("tg_voice.wav", format="wav")
                    
                    # РОЗПІЗНАВАННЯ ЧЕРЕЗ GOOGLE STT
                    with sr.AudioFile("tg_voice.wav") as source:
                        audio_data = recognizer.record(source)
                        text = recognizer.recognize_google(audio_data, language="uk-UA")
                    
                    bot.reply_to(message, f"🎤 Розпізнано: \"{text}\"")
                    process_command(message, text)
                    
                except Exception as e:
                    bot.reply_to(message, f"❌ Помилка розпізнавання голосу: {e}")
                finally:
                    if os.path.exists("tg_voice.ogg"): os.remove("tg_voice.ogg")
                    if os.path.exists("tg_voice.wav"): os.remove("tg_voice.wav")

            def process_command(message, cmd_text):
                try:
                    bot.send_chat_action(message.chat.id, 'typing')
                    cmd_lower = cmd_text.lower().strip()
                    for w in ["аве ", "ave ", "ави ", "аві "]:
                        if cmd_lower.startswith(w):
                            cmd_lower = cmd_lower[len(w):].strip()
                            break

                    status_callback("processing", "")
                    is_sys, sys_resp = execute_system_command(cmd_lower)
                    
                    if is_sys:
                        bot.send_message(message.chat.id, f"💻 {sys_resp}")
                    else:
                        ai_resp = generate_response(cmd_lower)
                        bot.send_message(message.chat.id, f"🤖 AVE: {ai_resp}")
                    status_callback("idle", "")
                
                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Системний збій при виконанні команди: {e}")
                    status_callback("idle", "")

            @bot.message_handler(commands=['start', 'help'])
            def send_welcome(message):
                if not check_auth(message): return
                bot.send_message(message.chat.id, "AVE OS активована. Готова до роботи.", reply_markup=get_main_keyboard())

            @bot.message_handler(func=lambda m: True)
            def handle_text(message):
                if not check_auth(message): return
                if message.text == '📊 Стан ПК': bot.reply_to(message, get_system_status())
                elif message.text == '📸 Фото': 
                    if surv.take_photo("snap.jpg"):
                        with open("snap.jpg", "rb") as p: bot.send_photo(message.chat.id, p)
                elif message.text == '🖼️ Скріншот':
                    if surv.take_screenshot("screen.png"):
                        with open("screen.png", "rb") as p: bot.send_photo(message.chat.id, p)
                elif message.text == '🛡 Охорона':
                    surv.SECURITY_MODE = not surv.SECURITY_MODE
                    bot.reply_to(message, f"🛡 Охорона: {'УВІМКНЕНО' if surv.SECURITY_MODE else 'ВИМКНЕНО'}")
                elif message.text == '❓ Допомога': send_welcome(message)
                else: process_command(message, message.text)

            print("[Telegram] Бот успішно працює на Google STT!")
            bot.polling(none_stop=True, timeout=60)
            
        except Exception as e:
            print(f"[Telegram] Помилка: {e}. Перезапуск через 5с...")
            time.sleep(5)