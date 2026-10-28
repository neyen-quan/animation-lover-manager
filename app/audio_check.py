"""Exercise Whisper's real decoder without downloading a speech model."""
import math
import struct
import tempfile
import wave
from pathlib import Path


def check_audio_decoder():
    from faster_whisper.audio import decode_audio

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'microphone.wav'
        samples = [int(6000 * math.sin(2 * math.pi * 440 * i / 16000))
                   for i in range(16000)]
        with wave.open(str(path), 'wb') as audio:
            audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            audio.writeframes(struct.pack('<16000h', *samples))
        decoded = decode_audio(str(path), sampling_rate=16000)
        if len(decoded) != 16000 or not (abs(decoded).max() > 0.1):
            raise RuntimeError('No se pudo decodificar el audio de prueba.')
