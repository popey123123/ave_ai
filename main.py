import time
import threading
import pyperclip
import re
from modules.stt import listen_and_recognize
from modules.ai_brain import generate_response
from modules.tts import speak
from modules.controller import execute_system_command
from modules.background import run_background_tasks

# Розширений словник для компенсації похибок STT
WAKE_WORDS = ["аве", "ave", "ави", "аві", "ава", "авве", "ав", "а ви", "авиа"]
CANCEL_WORDS = ["відміна", "скасувати", "зупинись", "стоп", "досить", "забудь", "відбій"]

def main(status_callback=None, app_state=None):
    if status_callback: status_callback("idle", "AVE OS: Системи ініціалізовано. Я готова до роботи.")
    
    def proactive_speak(msg):
        if status_callback: status_callback("speaking", msg)
        voice_text = re.sub(r'<[^>]+>', ' ', msg).strip()
        speak(voice_text)
        if status_callback: status_callback("idle", "")

    # Запуск фонових задач у незалежному потоці
    threading.Thread(target=run_background_tasks, args=(proactive_speak,), daemon=True).start()
    
    session_active = False
    silence_counter = 0
    
    while True:
        try:
            if app_state and not app_state.get('mic_active', True):
                if status_callback: status_callback("mic_off", "")
                time.sleep(1)
                continue

            if status_callback: status_callback("listening" if session_active else "idle", "")
            text = listen_and_recognize(language="uk-UA")
            
            if not text:
                if session_active:
                    silence_counter += 1
                    if silence_counter >= 2: 
                        session_active = False
                        silence_counter = 0
                        if status_callback: status_callback("idle", "Сесію закрито.")
                continue
            
            text_lower = text.lower().strip()
            print(f"[Log] Почуто: '{text_lower}'")
            silence_counter = 0
            command = ""
            
            if any(text_lower == w or text_lower.startswith(w + " ") for w in CANCEL_WORDS):
                session_active = False
                if status_callback: status_callback("idle", "Скасовано.")
                speak("Скасовано.")
                continue

            if not session_active:
                detected_trigger = next((w for w in WAKE_WORDS if text_lower == w or text_lower.startswith(w + " ")), None)
                if detected_trigger:
                    session_active = True
                    command = text_lower[len(detected_trigger):].strip()
                    if not command: 
                        speak("Слухаю.")
                        continue 
            else:
                command = text_lower
            
            if command:
                if status_callback: status_callback("user_input", command)
                if status_callback: status_callback("processing", "")
                
                # Захищений доступ до буфера обміну
                if "буфер" in command.lower():
                    try:
                        cb_text = pyperclip.paste()
                        if cb_text and isinstance(cb_text, str): 
                            command += f"\n\n[Текст з мого буфера обміну: {cb_text}]"
                    except Exception as e:
                        print(f"[Warning] Помилка доступу до буфера: {e}")

                is_system_cmd, sys_response = execute_system_command(command)
                final_response = sys_response if is_system_cmd else generate_response(command)
                
                if status_callback: status_callback("speaking", final_response)
                voice_text = re.sub(r'<[^>]+>', ' ', final_response).strip()
                speak(voice_text)
                
                if final_response.strip().endswith("?"):
                    session_active = True
                    silence_counter = 0

        except Exception as e:
            if status_callback: status_callback("idle", f"Системний збій STT: {e}")
            print(f"[Main Error] {e}")
        finally:
            time.sleep(0.1) # Запобігає перевантаженню процесора

if __name__ == "__main__":
    main()