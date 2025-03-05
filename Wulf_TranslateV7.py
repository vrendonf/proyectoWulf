import sounddevice as sd
import numpy as np
import queue
import whisper
import tkinter as tk
import threading
import time
from tkinter import scrolledtext, ttk
from googletrans import Translator
import soundfile as sf
import asyncio
from datetime import datetime
from docx import Document

# Configuración
SAMPLE_RATE = 16000
CHANNELS = 1
FILENAME = "temp_audio.wav"

# Variables globales
audio_queue = queue.Queue()
recording = False
mic_stream = None
input_mode = "mic"  # Puede ser "mic" o "system"
doc = Document()  # Documento de Word global

# Inicializar Whisper y Google Translate
model = whisper.load_model("medium")  # Puedes usar "small", "medium", "large"
translator = Translator()

# Revisar la lista de dispositivos disponibles y simplificarla
def get_audio_devices():
    devices = sd.query_devices()
    audio_devices = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0 or dev["max_output_channels"] > 0:
            audio_devices.append((i, dev["name"]))
    return audio_devices

# Capturar audio en la cola
def mic_callback(indata, *_):
    if recording:
        audio_queue.put(indata.copy())

# Guardar texto en documento de Word
def save_to_word(original_text, translated_text):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc.add_paragraph(f"Fecha y hora: {current_time}")
    doc.add_heading('Texto Original', level=2)
    doc.add_paragraph(original_text)
    doc.add_heading('Traducción', level=2)
    doc.add_paragraph(translated_text)
    doc.add_paragraph("-----------------------------")
    doc.save("transcripcion_traduccion.docx")

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
                
                # Guardar en documento de Word
                save_to_word(transcribed_text, translated_text)
        
        time.sleep(0.1)

# Iniciar grabación
def start_recording():
    global recording, mic_stream
    stop_recording()  # Asegurar que no haya otra grabación activa
    
    recording = True
    
    device_index = device_combobox.current()
    
    if device_index is not None and device_index >= 0:
        selected_device = audio_devices[device_index][0]
        print(f"🎧 Dispositivo seleccionado: {sd.query_devices(selected_device)['name']}")
        mic_stream = sd.InputStream(callback=mic_callback, samplerate=SAMPLE_RATE, channels=CHANNELS, device=selected_device)
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

# Interfaz gráfica
root = tk.Tk()
root.title("Wulf Translate")
root.geometry("600x500")

text_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=20)
text_box.pack(pady=10)

audio_devices = get_audio_devices()
device_names = [f"{name}" for _, name in audio_devices]

device_label = tk.Label(root, text="Selecciona el dispositivo de audio:")
device_label.pack(pady=5)

device_combobox = ttk.Combobox(root, values=device_names)
device_combobox.pack(pady=5)
device_combobox.current(0)

start_button = tk.Button(root, text="Iniciar Grabación", command=start_recording)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Detener Grabación", command=stop_recording)
stop_button.pack(pady=5)

# Iniciar procesamiento en un hilo
thread = threading.Thread(target=process_audio, daemon=True)
thread.start()

# Ejecutar interfaz
tk.mainloop()
