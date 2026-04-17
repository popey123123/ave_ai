import speech_recognition as sr
import warnings

warnings.filterwarnings("ignore")

def listen_and_recognize(language="uk-UA"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 [Google STT] Слухаю...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            # Слухаємо мікрофон
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            
            # Відправляємо на сервери Google
            text = r.recognize_google(audio, language=language)
            return text.strip()
        except Exception as e:
            return ""