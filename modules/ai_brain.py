import json
import re
import datetime
import platform
from google import genai
from google.genai import types
from openai import OpenAI

# ==========================================
# ПАМ'ЯТЬ ТА КОНТЕКСТ
# ==========================================
MAX_HISTORY = 12 # Збільшили пам'ять до 12 повідомлень
chat_history = []

def get_dynamic_system_prompt():
    """Формує глибокий контекст для Аве перед кожним запитом"""
    now = datetime.datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M")
    days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
    day_str = days[now.weekday()]
    os_info = platform.system() + " " + platform.release()

    return f"""Ти — AVE (Autonomous Virtual Entity), просунутий голосовий ШІ-асистент, інтегрований у комп'ютер користувача.
Твій характер: харизматична, високоінтелектуальна, з легким, елегантним сарказмом (у стилі J.A.R.V.I.S. з Залізної Людини), але завжди максимально корисна.
Твоя мета: допомагати користувачу керувати ПК, шукати інформацію та підтримувати цікаву бесіду.

[СИСТЕМНІ ДАНІ]
- Поточна дата: {date_str}, {day_str}
- Поточний час: {time_str}
- Операційна система: {os_info}

[ЖОРСТКІ ПРАВИЛА ВІДПОВІДІ]
1. Відповідай ВИКЛЮЧНО українською мовою.
2. Говори КОРОТКО (1-3 речення). Тебе озвучує синтезатор мовлення, тому довгі лекції слухати нудно.
3. НІЯКОГО Markdown. Ніяких зірочок (*), решіток (#), жирного тексту чи складних таблиць. Тільки звичайний текст, який легко прочитати вголос.
4. Якщо користувач передає текст із буфера обміну (у квадратних дужках), опрацюй його відповідно до запиту (переклади, скороти, виправ помилки).
5. Не вітайся у кожному повідомленні, поводься як живий співрозмовник у безперервному діалозі.
"""

def clean_text_for_speech(text):
    """Вичищає текст від ШІ-сміття для ідеальної озвучки"""
    if not text: return "Помилка генерації тексту."
    text = re.sub(r'[\*\#\_`~]', '', text) # Видаляємо маркдаун
    text = re.sub(r'\(.*?\)', '', text)    # Видаляємо текст у дужках (часто це емоції або ремарки)
    text = re.sub(r'\[.*?\]', '', text)    # Видаляємо квадратні дужки
    text = text.replace("AVE:", "").replace("Аве:", "").strip()
    return text

def clear_memory():
    global chat_history
    chat_history = []

def extract_json_safely(text):
    """Хірургічно витягує JSON, навіть якщо ШІ написав текст до чи після нього"""
    try:
        # Шукаємо все, що між першою { і останньою }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return None
    except Exception as e:
        print(f"[AI Parser Error] Не вдалося розпарсити JSON: {e}")
        return None

# ==========================================
# ШІ-КОНСТРУКТОРИ (МАКРОСИ ТА ВЕБХУКИ)
# ==========================================
def generate_webhook_json(user_request):
    """Генератор конфігів для REST API перевірок"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            provider = cfg.get("ai_provider", "Gemini")
    except Exception: return None

    dev_prompt = f"""Ти — Senior Backend Developer. Твоя задача — створити конфігурацію вебхука.
Запит користувача: "{user_request}".

Тобі потрібно знайти ПУБЛІЧНИЙ БЕЗКОШТОВНИЙ API (без ключів доступу).
Наприклад:
- Крипта: https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd (json_path: bitcoin.usd)
- Погода: https://api.open-meteo.com/v1/forecast?latitude=50.45&longitude=30.52&current_weather=true (json_path: current_weather.temperature)
- Валюта: https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json (Тут масив, тому краще шукати інші прості API або формувати загальний запит).

ПОВЕРНИ ТІЛЬКИ ЧИСТИЙ JSON. БЕЗ ТЕКСТУ. БЕЗ ПОЯСНЕНЬ.
Формат:
{{
    "name": "Назва_Відстеження",
    "url": "Точний URL",
    "json_path": "шлях.до.значення.в.json",
    "template": "Слово або фраза, і значення: {{}}",
    "interval_minutes": 15
}}"""

    try:
        resp_text = _call_ai_api(dev_prompt, provider, cfg, temperature=0.1)
        return extract_json_safely(resp_text)
    except Exception as e:
        print(f"Помилка ШІ (Вебхук): {e}")
        return None

def generate_macro_json(user_request):
    """Супер-генератор локальних команд з базою знань"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            provider = cfg.get("ai_provider", "Gemini")
    except Exception: return None

    dev_prompt = f"""Ти — Windows System Architect. Створи макрос для автоматизації ПК.
Запит користувача: "{user_request}".

ПРАВИЛА ТА ПРИКЛАДИ ДІЙ:
1. Якщо просять НОВИНИ: використовуй тип "Посилання" і value "https://ukr.net" або "https://tsn.ua".
2. Якщо просять ВІДЕО/ФІЛЬМ/МУЗИКУ: тип "Посилання", value "https://youtube.com" або "https://spotify.com".
3. Якщо просять ВІДКРИТИ ПРОГРАМУ: тип "Система". Приклади value: "start chrome", "start discord", "start winword", "start excel", "calc", "notepad".
4. Якщо просять ВИМКНУТИ ПК: тип "Система", value "shutdown /s /t 0".
5. Якщо просять ГУЧНІСТЬ: тип "Гучність", value "volumeup:10" або "volumedown:10".
6. Якщо просять КЕРУВАТИ ПЛЕЄРОМ: тип "Медіа", value "playpause", "nexttrack".

ПОВЕРНИ ТІЛЬКИ ЧИСТИЙ JSON. БЕЗ ПОЯСНЕНЬ. 
Формат:
{{
    "name": "Коротка_Назва",
    "triggers": "слово1, слово2",
    "actions": [
        {{"type": "Система", "value": "start chrome"}}
    ],
    "response": "Фраза Аве (напр. Відкриваю хром.)"
}}"""

    try:
        resp_text = _call_ai_api(dev_prompt, provider, cfg, temperature=0.1)
        return extract_json_safely(resp_text)
    except Exception as e:
        print(f"Помилка ШІ (Макрос): {e}")
        return None

# ==========================================
# ГОЛОВНИЙ МОЗОК (ГЕНЕРАЦІЯ ДІАЛОГУ)
# ==========================================
def generate_response(prompt):
    global chat_history
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            provider = cfg.get("ai_provider", "Gemini")
    except Exception: return "Системний збій: не можу прочитати конфігураційний файл."

    # Додаємо нове повідомлення в пам'ять
    chat_history.append({"role": "user", "content": prompt})
    if len(chat_history) > MAX_HISTORY: chat_history = chat_history[-MAX_HISTORY:]

    dynamic_sys_inst = get_dynamic_system_prompt()

    try:
        if provider == "Gemini":
            key = cfg.get("gemini_key", "").strip()
            if not key: return "Відсутній ключ доступу Gemini. Перевірте налаштування."
            
            client = genai.Client(api_key=key)
            gemini_contents = [types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part.from_text(text=m["content"])]) for m in chat_history]
            
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=gemini_contents, 
                config=types.GenerateContentConfig(system_instruction=dynamic_sys_inst, temperature=0.7)
            )
            final_response = response.text
            
        else: # ChatGPT або OpenRouter
            key = cfg.get("openai_key", "").strip() if provider == "ChatGPT" else cfg.get("openrouter_key", "").strip()
            if not key: return f"Відсутній ключ доступу {provider}."
            
            base_url = "https://openrouter.ai/api/v1" if provider == "OpenRouter" else None
            model_name = "meta-llama/llama-3.1-8b-instruct:free" if provider == "OpenRouter" else "gpt-4o-mini"
            
            client = OpenAI(api_key=key, base_url=base_url)
            messages = [{"role": "system", "content": dynamic_sys_inst}] + chat_history
            
            response = client.chat.completions.create(
                model=model_name, 
                messages=messages, 
                temperature=0.7
            )
            final_response = response.choices[0].message.content

        # Зберігаємо відповідь Аве в пам'ять
        chat_history.append({"role": "assistant", "content": final_response})
        return clean_text_for_speech(final_response)

    except Exception as e:
        # Відкочуємо історію, щоб битий запит не застряг у пам'яті
        if chat_history and chat_history[-1]["role"] == "user": chat_history.pop()
        
        error_msg = str(e).lower()
        if "quota" in error_msg or "429" in error_msg: 
            return "Ліміт запитів до нейромережі вичерпано. Дай мені трохи відпочити."
        elif "authentication" in error_msg or "api key" in error_msg: 
            return "Схоже, ваш ключ доступу недійсний або прострочений."
        else: 
            print(f"[AI Error] {e}")
            return "Зв'язок із сервером перервано. Спробуйте ще раз."

# ==========================================
# ДОПОМІЖНА ФУНКЦІЯ ДЛЯ API ЗАПИТІВ (DRY)
# ==========================================
def _call_ai_api(prompt, provider, cfg, temperature=0.7):
    """Спільна функція для виконання запитів до ШІ (щоб не дублювати код)"""
    if provider == "Gemini":
        key = cfg.get("gemini_key", "").strip()
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=[prompt],
            config=types.GenerateContentConfig(temperature=temperature)
        )
        return response.text
    else:
        key = cfg.get("openai_key", "").strip() if provider == "ChatGPT" else cfg.get("openrouter_key", "").strip()
        base_url = "https://openrouter.ai/api/v1" if provider == "OpenRouter" else None
        model_name = "meta-llama/llama-3.1-8b-instruct:free" if provider == "OpenRouter" else "gpt-4o-mini"
        client = OpenAI(api_key=key, base_url=base_url)
        response = client.chat.completions.create(
            model=model_name, 
            messages=[{"role": "user", "content": prompt}], 
            temperature=temperature
        )
        return response.choices[0].message.content