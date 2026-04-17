import os, webbrowser, datetime, urllib.parse, requests, json, pyautogui, time, re, winreg, threading
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pywhatkit
import psutil
import pygame
import comtypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from modules.background import add_reminder
import modules.surveillance as surv 

LAST_INTENT = None
STEAM_GAMES = {}
DIALOG_STATE = {"intent": None, "data": None}

# Безпечна ініціалізація аудіо (не впаде, якщо немає колонок)
try:
    pygame.mixer.init()
except Exception as e:
    print(f"[Audio Init Warning] Не знайдено пристрій виводу звуку: {e}")

def set_absolute_volume(level):
    try:
        comtypes.CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        if hasattr(devices, 'Activate'):
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        else:
            interface = devices._device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        val = max(0, min(level, 100)) / 100.0
        volume.SetMasterVolumeLevelScalar(val, None)
        return True
    except Exception as e:
        print(f"[Volume Error] Помилка зміни гучності: {e}")
        return False
    finally:
        try: comtypes.CoUninitialize()
        except: pass

def init_steam_games():
    global STEAM_GAMES
    STEAM_GAMES.clear()
    paths = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            paths.append(steam_path.replace('/', '\\'))
    except:
        paths.extend([r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"])

    for base in paths:
        vdf = os.path.join(base, "steamapps", "libraryfolders.vdf")
        lib_paths = [base]
        if os.path.exists(vdf):
            try:
                with open(vdf, 'r', encoding='utf-8') as f: content = f.read()
                lib_paths.extend(re.findall(r'"path"\s+"([^"]+)"', content))
            except: pass

        for lib in set(lib_paths):
            app_dir = os.path.join(lib.replace('\\\\', '\\'), "steamapps")
            if os.path.exists(app_dir):
                for file in os.listdir(app_dir):
                    if file.startswith("appmanifest_") and file.endswith(".acf"):
                        try:
                            with open(os.path.join(app_dir, file), 'r', encoding='utf-8') as af:
                                acf = af.read()
                                name = re.search(r'"name"\s+"([^"]+)"', acf)
                                appid = re.search(r'"appid"\s+"([^"]+)"', acf)
                                if name and appid: STEAM_GAMES[name.group(1).lower()] = appid.group(1)
                        except: pass
        if STEAM_GAMES: break

threading.Thread(target=init_steam_games, daemon=True).start()

def load_cfg():
    try:
        with open('config.json', 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def get_system_status():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    battery = psutil.sensors_battery()
    bat_str = f"Батарея: {battery.percent}%." if battery else "ПК працює від мережі."
    return f"Статус системи: Навантаження процесора {cpu}%, Оперативна пам'ять {ram}%. {bat_str}"

def get_weather_owm(city="Суми", cmd=""):
    cfg = load_cfg(); key = cfg.get("owm_key")
    if not key: return "Ключ метео не встановлено."
    try:
        if "завтра" in cmd:
            r = requests.get(f"[http://api.openweathermap.org/data/2.5/forecast?q=](http://api.openweathermap.org/data/2.5/forecast?q=){urllib.parse.quote(city)}&appid={key}&units=metric&lang=uk", timeout=5)
            if r.status_code == 200:
                tom = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                f = next((i for i in r.json()['list'] if i['dt_txt'].startswith(tom) and "12:00:00" in i['dt_txt']), None) or next((i for i in r.json()['list'] if i['dt_txt'].startswith(tom)), None)
                if f: return f"Завтра у місті {city} {round(f['main']['temp'])} градусів, {f['weather'][0]['description']}."
            return "Не вдалося отримати прогноз."
        else:
            r = requests.get(f"[http://api.openweathermap.org/data/2.5/weather?q=](http://api.openweathermap.org/data/2.5/weather?q=){urllib.parse.quote(city)}&appid={key}&units=metric&lang=uk", timeout=5)
            if r.status_code == 200: d = r.json(); return f"Зараз у місті {city} {round(d['main']['temp'])} градусів, {d['weather'][0]['description']}."
    except: return "Помилка підключення до метеосервера."

def get_today_holiday():
    try:
        m = ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
        n = datetime.datetime.now(); d = n.day; mon = m[n.month - 1]
        r = requests.get(f"[https://uk.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles=](https://uk.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles=){d}_{urllib.parse.quote(mon)}&format=json", timeout=5)
        if r.status_code == 200:
            p = r.json().get("query", {}).get("pages", {})
            for pid, info in p.items():
                ext = info.get("extract", "")
                if ext: return f"Сьогодні {d} {mon}. " + ". ".join(ext.split(". ")[:2]) + "."
        return f"Сьогодні {d} {mon}."
    except: return "Немає доступу до бази знань."

def parse_rss_news(url):
    r = requests.get(url, timeout=5)
    root = ET.fromstring(r.content)
    items = []
    for item in root.findall('./channel/item')[:4]:
        desc_html = item.find('description').text or ""
        desc_text = BeautifulSoup(desc_html, 'html.parser').text.strip()
        sentences = [s for s in desc_text.split('. ') if s]
        items.append({"title": item.find('title').text.strip(), "link": item.find('link').text.strip(), "desc": ". ".join(sentences[:2]) + "." if sentences else "Деталей немає."})
    return items

def _play_youtube_async(song):
    """Викликає YouTube в окремому потоці, щоб не фризити Аве"""
    try: pywhatkit.playonyt(song)
    except Exception as e: print(f"YouTube Error: {e}")

def execute_system_command(command):
    global LAST_INTENT, DIALOG_STATE
    cmd = command.lower().strip()
    
    if "звук на" in cmd or "гучність" in cmd:
        match = re.search(r'(\d+)', cmd)
        if match:
            level = int(match.group(1))
            if set_absolute_volume(level):
                return True, f"Встановила гучність на {level} відсотків."

    if "я відійду" in cmd or "я йду" in cmd:
        pyautogui.press('playpause')
        if os.path.exists("goodbye.mp3"):
            set_absolute_volume(100)
            try:
                pygame.mixer.music.load("goodbye.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy(): time.sleep(0.5)
            except: pass
        set_absolute_volume(0) 
        surv.SECURITY_MODE = True
        return True, "Буду чекати вашого повернення."

    if "я повернувся" in cmd or "я тут" in cmd:
        surv.SECURITY_MODE = False
        set_absolute_volume(30)
        if os.path.exists("welcome.mp3"):
            set_absolute_volume(100)
            try:
                pygame.mixer.music.load("welcome.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy(): time.sleep(0.5)
            except: pass
            set_absolute_volume(30)
            return True, "З поверненням, сер! Системи в нормі."
        return True, "З поверненням!"

    if "статус системи" in cmd or "стан пк" in cmd:
        return True, get_system_status()
        
    if "вимкни комп" in cmd or "виключи пк" in cmd:
        os.system("shutdown /s /t 5")
        return True, "Вимикаю систему."

    if cmd.startswith("включи ") or cmd.startswith("увімкни ") or cmd.startswith("заграй "):
        song = cmd.replace("включи ", "").replace("увімкни ", "").replace("заграй ", "").strip()
        if "комп" not in song and "пк" not in song:
            threading.Thread(target=_play_youtube_async, args=(song,), daemon=True).start()
            return True, f"Шукаю і вмикаю {song} на YouTube."

    if "запусти гру" in cmd or "відкрий гру" in cmd:
        game_query = cmd.replace("запусти гру", "").replace("відкрий гру", "").strip()
        for g_name, appid in STEAM_GAMES.items():
            if game_query in g_name or g_name in game_query:
                os.system(f"start steam://rungameid/{appid}")
                return True, f"Запускаю {g_name} через Steam."
        return True, f"Не знайшла гру '{game_query}' у Steam."

    if DIALOG_STATE.get("intent") == "news_open":
        url = DIALOG_STATE["data"]
        DIALOG_STATE.update({"intent": None, "data": None})
        if "так" in cmd or "відкрий" in cmd or "давай" in cmd:
            webbrowser.open(url)
            return True, "Відкриваю повну статтю."
        else: return True, "Добре, продовжуємо."

    if DIALOG_STATE.get("intent") == "news_select":
        items = DIALOG_STATE["data"]
        index = -1
        if "перш" in cmd or "1" in cmd or "один" in cmd: index = 0
        elif "друг" in cmd or "2" in cmd or "два" in cmd: index = 1
        elif "трет" in cmd or "3" in cmd or "три" in cmd: index = 2
        elif "четверт" in cmd or "4" in cmd or "чотири" in cmd or "останню" in cmd: index = 3
        
        if index != -1 and index < len(items):
            news = items[index]
            DIALOG_STATE.update({"intent": "news_open", "data": news["link"]})
            return True, f"{news['desc']} <br><br><a href='{news['link']}' style='color: #b052ff; font-weight: bold; text-decoration: none;'>🔗 Читати повністю на сайті</a><br><i>Відкрити цю новину?</i>"
        else:
            DIALOG_STATE.update({"intent": None, "data": None})
            return False, "" 

    if DIALOG_STATE.get("intent") == "news_category" or "новин" in cmd:
        cat_map = {
            "війн": ("Війна", "[https://tsn.ua/rss/ato.rss](https://tsn.ua/rss/ato.rss)"), "політ": ("Політика", "[https://tsn.ua/rss/politika.rss](https://tsn.ua/rss/politika.rss)"),
            "економ": ("Економіка", "[https://tsn.ua/rss/groshi.rss](https://tsn.ua/rss/groshi.rss)"),
            "світ": ("Світ", "[https://tsn.ua/rss/svit.rss](https://tsn.ua/rss/svit.rss)"), "спорт": ("Спорт", "[https://tsn.ua/rss/prosport.rss](https://tsn.ua/rss/prosport.rss)"),
            "технологі": ("Технології", "[https://tsn.ua/rss/nauka_it.rss](https://tsn.ua/rss/nauka_it.rss)")
        }
        target_name = None; url = None
        for k, v in cat_map.items():
            if k in cmd: target_name, url = v; break
            
        if target_name and url:
            try:
                items = parse_rss_news(url)
                if items:
                    DIALOG_STATE.update({"intent": "news_select", "data": items})
                    titles = [f"{i+1}. {x['title']}" for i, x in enumerate(items)]
                    return True, f"Головне в категорії '{target_name}':<br><br>" + "<br><br>".join(titles) + "<br><br><b>Про яку розповісти детальніше?</b>"
            except: return True, "Помилка завантаження новин."
        
        if "новин" in cmd and not target_name:
            DIALOG_STATE["intent"] = "news_category"
            return True, "Які саме новини вас цікавлять? Головне, війна, політика чи економіка?"

    if "нагадай" in cmd and "через" in cmd:
        match = re.search(r'через\s+(\d+)\s+(хвилин|хвилину|хвилини|хв|секунд|секунди|сек)', cmd)
        if match:
            amount = int(match.group(1)); unit = match.group(2)
            task = cmd.replace(match.group(0), "").replace("нагадай мені", "").replace("нагадай", "").replace("щоб", "").strip()
            sec = amount if "сек" in unit else amount * 60
            add_reminder(task, sec)
            return True, f"Записала. Нагадаю {task} через {amount} {'секунд' if 'сек' in unit else 'хвилин'}."

    cfg = load_cfg()
    system_overrides = ["погода", "час", "годин", "свято", "свята", "новин", "новини"]
    is_sys = any(w in cmd for w in system_overrides)
    if not is_sys:
        qw = {"хто", "як", "чому", "коли", "де", "скільки", "який", "яка", "яке", "чи", "що", "навіщо", "знайди", "пошукай"}
        phr = ["що таке", "хто такий", "розкажи", "порадь", "напиши", "придумай", "поясни", "дай", "топ", "порівняй", "переклади"]
        if set(cmd.split()).intersection(qw) or any(p in cmd for p in phr): return False, ""

    for cat, macros in cfg.get("commands", {}).items():
        for m_name, m_data in macros.items():
            trigs = sorted([t.strip().lower() for t in m_data.get("triggers", "").split(",") if t.strip()], key=len, reverse=True)
            # Захист: шукаємо слово як окреме (щоб "час" не спрацював на "почастуй")
            matched = next((t for t in trigs if re.search(rf'(?:^|\W){re.escape(t)}(?:$|\W)', cmd)), None)
            
            if matched:
                dyn_resp = ""
                for act in m_data.get("actions", []):
                    at, av = act.get("type", ""), str(act.get("value", "")).strip()
                    try:
                        if at == "Посилання": webbrowser.open(av)
                        elif at == "Файл": os.startfile(av)
                        elif at == "Система": os.system(av)
                        elif at == "Медіа": pyautogui.press(av)
                        elif at == "Гучність":
                            if "volumeset" in av:
                                try: set_absolute_volume(int(av.split(":")[1]))
                                except: pass
                            elif "up" in av: pyautogui.press('volumeup')
                            else: pyautogui.press('volumedown')
                        elif at == "Затримка": time.sleep(float(av))
                        elif at == "Функція":
                            if av == "погода": dyn_resp = get_weather_owm("Чернівці" if "чернівц" in cmd else "Суми", cmd)
                            elif av == "час": dyn_resp = f"Зараз {datetime.datetime.now().strftime('%H:%M')}."
                            elif av == "свято": dyn_resp = get_today_holiday()
                            elif av == "пошук":
                                q = cmd.replace(matched, "").replace("в гуглі", "").replace("знайди", "").replace("пошукай", "").strip()
                                if q: webbrowser.open(f"[https://www.google.com/search?q=](https://www.google.com/search?q=){urllib.parse.quote(q)}")
                                dyn_resp = f"Шукаю {q}" if q else "Що саме знайти?"
                    except Exception as e: print(f"[Macro Action Error] Помилка дії {at}: {e}")
                
                res = f"{m_data.get('response', '')} {dyn_resp}".strip()
                return True, res if res else "Виконано."

    return False, ""