import sounddevice as sd
import numpy as np
import queue
import whisper
import tkinter as tk
import threading
import time
from tkinter import scrolledtext
from googletrans import Translator
import soundfile as sf
import asyncio

# Configuración
SAMPLE_RATE = 16000
CHANNELS = 1
FILENAME = "temp_audio.wav"

# Variables globales
audio_queue = queue.Queue()
recording = False
mic_stream = None
input_mode = "mic"  # Puede ser "mic" o "system"

# Inicializar Whisper y Google Translate
model = whisper.load_model("medium")  # Puedes usar "small", "medium", "large"
translator = Translator()

# Detectar micrófono
def get_mic_index():
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            return i
    return None

# Detectar audio del sistema
def get_system_audio_index():
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if "loopback" in dev.get("name", "").lower():
            return i
    return None

# Capturar audio en la cola
def mic_callback(indata, *_):
    if recording:
        audio_queue.put(indata.copy())

# Procesar audio
def process_audio():
    while True:
        if not audio_queue.empty():
            audio_data = []
            while not audio_queue.empty():
                audio_data.append(audio_queue.get())
            
            if audio_data:
                audio_array = np.concatenate(audio_data, axis=0)
                sf.write(FILENAME, audio_array, SAMPLE_RATE)

                # Transcripción y traducción
                result = model.transcribe(FILENAME)
                transcribed_text = result["text"].strip()
                
                if transcribed_text:
                    detected_lang = translator.detect(transcribed_text).lang
                    target_lang = "es" if detected_lang == "en" else "en"
                    translated_text = translator.translate(transcribed_text, dest=target_lang).text
                else:
                    translated_text = "⚠️ No se detectó texto."

                # Mostrar en la interfaz
                text_box.insert(tk.END, f"🎧 Original: {transcribed_text}\n")
                text_box.insert(tk.END, f"🌍 Traducción: {translated_text}\n")
                text_box.insert(tk.END, "-----------------------------\n")
                text_box.yview(tk.END)
        
        time.sleep(0.1)

# Iniciar grabación
def start_recording():
    global recording, mic_stream
    stop_recording()  # Asegurar que no haya otra grabación activa
    
    recording = True
    
    device_index = get_mic_index() if input_mode == "mic" else get_system_audio_index()
    
    if device_index is not None:
        mic_stream = sd.InputStream(callback=mic_callback, samplerate=SAMPLE_RATE, channels=CHANNELS, device=device_index)
        mic_stream.start()
        print(f"🎧 Grabando desde {'micrófono' if input_mode == 'mic' else 'audio del sistema'}...")
    else:
        print("⚠️ No se seleccionó un dispositivo de entrada.")
        recording = False

# Detener grabación
def stop_recording():
    global recording, mic_stream
    if mic_stream:
        mic_stream.stop()
        mic_stream.close()
    recording = False

# Cambiar entre micrófono y audio del sistema
def toggle_input():
    global input_mode, toggle_button
    input_mode = "mic" if input_mode == "system" else "system"
    toggle_button.config(text=f"Usar {'Audio del Sistema' if input_mode == 'mic' else 'Micrófono'}")
    print(f"🔄 Cambiado a {'micrófono' if input_mode == 'mic' else 'audio del sistema'}")
    stop_recording()

# Interfaz gráfica
root = tk.Tk()
root.title("Wulf Translate")
root.geometry("600x500")

text_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=20)
text_box.pack(pady=10)

start_button = tk.Button(root, text="Iniciar Grabación", command=start_recording)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Detener Grabación", command=stop_recording)
stop_button.pack(pady=5)

toggle_button = tk.Button(root, text="Usar Audio del Sistema", command=toggle_input)
toggle_button.pack(pady=5)

# Iniciar procesamiento en un hilo
thread = threading.Thread(target=process_audio, daemon=True)
thread.start()

# Ejecutar interfaz
tk.mainloop()
