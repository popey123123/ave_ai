import time
import requests
import json

last_known_values = {}
active_reminders = []

def add_reminder(task, seconds):
    """Додає нове нагадування в чергу"""
    active_reminders.append({"task": task, "time": time.time() + seconds})

def get_nested_value(data, path):
    try:
        val = data
        for k in path.split('.'): val = val[k]
        return str(val)
    except: return None

def run_background_tasks(say_callback):
    time.sleep(5) 
    
    while True:
        try:
            current_time = time.time()
            
            # 1. ПЕРЕВІРКА НАГАДУВАНЬ
            for r in active_reminders[:]:
                if current_time >= r["time"]:
                    say_callback(f"Нагадую: {r['task']}")
                    active_reminders.remove(r)

            # 2. ПЕРЕВІРКА ВЕБХУКІВ
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except:
                cfg = {}
            
            for hook in cfg.get("webhooks", []):
                name = hook.get("name", "Unknown")
                url = hook.get("url", "")
                json_path = hook.get("json_path", "")
                template = hook.get("template", "Сповіщення: {}")
                interval = hook.get("interval_minutes", 60)
                
                last_time = last_known_values.get(f"{name}_time", 0)
                
                if current_time - last_time >= (interval * 60):
                    last_known_values[f"{name}_time"] = current_time 
                    try:
                        r = requests.get(url, timeout=5)
                        if r.status_code == 200:
                            val = get_nested_value(r.json(), json_path)
                            if val and val != last_known_values.get(f"{name}_val"):
                                last_known_values[f"{name}_val"] = val
                                say_callback(template.replace("{}", str(val)))
                    except: pass
                                
        except Exception as e:
            pass # Ігноруємо дрібні помилки, щоб потік не падав
            
        time.sleep(1) # Перевіряємо таймери кожну секунду