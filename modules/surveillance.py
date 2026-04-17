import cv2
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import time
import os
import threading
import pyautogui 

SECURITY_MODE = False
SECURITY_CALLBACK = None 

def take_photo(filename="photo.jpg"):
    try:
        cap = cv2.VideoCapture(0)
        time.sleep(1)
        ret, frame = cap.read()
        if ret: cv2.imwrite(filename, frame)
        cap.release()
        return ret
    except: return False

def take_screenshot(filename="screenshot.png"):
    try:
        screen = pyautogui.screenshot()
        screen.save(filename)
        return True
    except: return False

def record_audio(filename="audio.wav", duration=5, fs=44100):
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype=np.int16)
        sd.wait()
        write(filename, fs, recording)
        return True
    except: return False

def record_video(filename="video.avi", duration=5):
    try:
        cap = cv2.VideoCapture(0)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if ret: out.write(frame)
            else: break
        cap.release()
        out.release()
        return True
    except: return False

def security_listen_loop():
    global SECURITY_MODE
    fs = 16000
    threshold = 3000
    while True:
        if SECURITY_MODE:
            try:
                chunk = sd.rec(int(1 * fs), samplerate=fs, channels=1, dtype=np.int16)
                sd.wait()
                volume = np.max(np.abs(chunk))
                if volume > threshold:
                    if SECURITY_CALLBACK:
                        SECURITY_CALLBACK("🚨 Увага! Виявлено шум у кімнаті. Записую аудіо...")
                        record_audio("alert_audio.wav", duration=10)
                        SECURITY_CALLBACK("file:alert_audio.wav")
                    time.sleep(60) 
            except: pass
        time.sleep(1)

threading.Thread(target=security_listen_loop, daemon=True).start()