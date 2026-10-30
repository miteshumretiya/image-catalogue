"""Generate assets/done.wav, the short chime played when a scan finishes.

I made the sound myself with the standard library so there are no
copyright issues. Run once:  python tools/make_sound.py
"""
import math
import os
import struct
import wave

SAMPLE_RATE = 44100


def tone(frequency, seconds, volume=0.4):
    samples = []
    count = int(SAMPLE_RATE * seconds)
    for i in range(count):
        fade = 1 - i / count    # fade out so it doesn't click at the end
        value = volume * fade * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)
        samples.append(int(value * 32767))
    return samples


def main():
    samples = tone(660, 0.15) + tone(880, 0.30)    # two rising notes
    out_path = os.path.join(os.path.dirname(__file__), "..", "assets", "done.wav")
    with wave.open(out_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    print("Saved", os.path.abspath(out_path))


if __name__ == "__main__":
    main()
