import speech_recognition as sr

print("Список усіх аудіопристроїв:")
for index, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"[{index}] {name}")