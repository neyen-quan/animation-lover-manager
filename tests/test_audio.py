import tempfile
import unittest
from pathlib import Path

from app.audio_check import check_audio_decoder


class AudioTests(unittest.TestCase):
    def test_real_microphone_wav_decoder(self):
        # Reproduces the metadata_errors failure with incompatible PyAV 19.
        check_audio_decoder()

    def test_real_whatsapp_opus_decoder(self):
        import av
        import numpy as np
        from faster_whisper.audio import decode_audio

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'voice.ogg'
            with av.open(str(path), 'w', format='ogg') as container:
                stream = container.add_stream('libopus', rate=48000)
                stream.layout = 'mono'
                samples = (6000 * np.sin(2 * np.pi * 440 * np.arange(48000) / 48000)).astype(np.int16)
                frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format='s16', layout='mono')
                frame.sample_rate = 48000
                for packet in stream.encode(frame):
                    container.mux(packet)
                for packet in stream.encode(None):
                    container.mux(packet)
            decoded = decode_audio(str(path), sampling_rate=16000)
            self.assertAlmostEqual(len(decoded), 16000, delta=320)
            self.assertGreater(float(abs(decoded).max()), 0.1)
