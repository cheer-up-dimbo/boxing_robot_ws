#!/usr/bin/env python3
"""Generate WAV sound effects for BoxBunny GUI.

All sounds are 16-bit PCM, 44100Hz, mono.
Each uses sine wave generation with attack/decay envelopes.
"""

import wave
import struct
import math
import os

SAMPLE_RATE = 44100
AMPLITUDE = 32767  # max for 16-bit
SOUNDS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "boxbunny_gui", "assets", "sounds"
)


def make_envelope(num_samples, attack_ms=5, decay_ms=50):
    """Create an attack/decay envelope."""
    attack_samples = int(SAMPLE_RATE * attack_ms / 1000)
    decay_samples = int(SAMPLE_RATE * decay_ms / 1000)
    envelope = []
    for i in range(num_samples):
        if i < attack_samples:
            env = i / max(attack_samples, 1)
        elif i > num_samples - decay_samples:
            env = (num_samples - i) / max(decay_samples, 1)
        else:
            env = 1.0
        envelope.append(max(0.0, min(1.0, env)))
    return envelope


def generate_tone(freq, duration_ms, volume=1.0, attack_ms=5, decay_ms=50):
    """Generate a sine wave tone with envelope."""
    num_samples = int(SAMPLE_RATE * duration_ms / 1000)
    envelope = make_envelope(num_samples, attack_ms, decay_ms)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        value = math.sin(2 * math.pi * freq * t)
        value *= envelope[i] * volume * AMPLITUDE
        samples.append(int(max(-32768, min(32767, value))))
    return samples


def generate_silence(duration_ms):
    """Generate silence."""
    num_samples = int(SAMPLE_RATE * duration_ms / 1000)
    return [0] * num_samples


def generate_sweep(freq_start, freq_end, duration_ms, volume=1.0, attack_ms=5, decay_ms=50):
    """Generate a frequency sweep with envelope."""
    num_samples = int(SAMPLE_RATE * duration_ms / 1000)
    envelope = make_envelope(num_samples, attack_ms, decay_ms)
    samples = []
    phase = 0.0
    for i in range(num_samples):
        t = i / num_samples
        freq = freq_start + (freq_end - freq_start) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        value = math.sin(phase)
        value *= envelope[i] * volume * AMPLITUDE
        samples.append(int(max(-32768, min(32767, value))))
    return samples


def write_wav(filename, samples):
    """Write samples to a WAV file."""
    filepath = os.path.join(SOUNDS_DIR, filename)
    with wave.open(filepath, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(SAMPLE_RATE)
        data = struct.pack('<' + 'h' * len(samples), *samples)
        wav.writeframes(data)
    size = os.path.getsize(filepath)
    print(f"  Created {filename} ({size} bytes, {len(samples)} samples)")


def bell_start():
    """3 short high-pitched dings (880Hz, 150ms each, 100ms gaps)."""
    samples = []
    for i in range(3):
        samples.extend(generate_tone(880, 150, volume=0.8, attack_ms=2, decay_ms=80))
        if i < 2:
            samples.extend(generate_silence(100))
    write_wav("bell_start.wav", samples)


def bell_end():
    """1 longer ding (880Hz, 400ms)."""
    samples = generate_tone(880, 400, volume=0.8, attack_ms=5, decay_ms=200)
    write_wav("bell_end.wav", samples)


def countdown_beep():
    """Sharp beep (1000Hz, 100ms)."""
    samples = generate_tone(1000, 100, volume=0.7, attack_ms=2, decay_ms=30)
    write_wav("countdown_beep.wav", samples)


def countdown_go():
    """Higher louder beep (1200Hz, 200ms)."""
    samples = generate_tone(1200, 200, volume=0.9, attack_ms=3, decay_ms=60)
    write_wav("countdown_go.wav", samples)


def button_click():
    """Very short click (2000Hz, 30ms, low volume)."""
    samples = generate_tone(2000, 30, volume=0.3, attack_ms=1, decay_ms=15)
    write_wav("button_click.wav", samples)


def session_complete():
    """Rising chime (440Hz to 880Hz sweep, 500ms)."""
    samples = generate_sweep(440, 880, 500, volume=0.8, attack_ms=10, decay_ms=150)
    write_wav("session_complete.wav", samples)


def impact():
    """Low thud (150Hz, 80ms, with quick decay)."""
    samples = generate_tone(150, 80, volume=0.9, attack_ms=1, decay_ms=60)
    write_wav("impact.wav", samples)


def reaction_stimulus():
    """Sharp alert (1500Hz, 150ms)."""
    samples = generate_tone(1500, 150, volume=0.8, attack_ms=2, decay_ms=40)
    write_wav("reaction_stimulus.wav", samples)


def coach_notification():
    """Gentle two-note (660Hz 100ms, 880Hz 100ms)."""
    samples = generate_tone(660, 100, volume=0.6, attack_ms=5, decay_ms=30)
    samples.extend(generate_tone(880, 100, volume=0.6, attack_ms=5, decay_ms=30))
    write_wav("coach_notification.wav", samples)


def rest_start():
    """Gentle low tone (330Hz, 300ms)."""
    samples = generate_tone(330, 300, volume=0.5, attack_ms=10, decay_ms=150)
    write_wav("rest_start.wav", samples)


def main():
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    print(f"Generating sounds in: {SOUNDS_DIR}")
    print()

    bell_start()
    bell_end()
    countdown_beep()
    countdown_go()
    button_click()
    session_complete()
    impact()
    reaction_stimulus()
    coach_notification()
    rest_start()

    print()
    print("All sound files generated successfully!")

    # Verify sizes
    total = 0
    for f in os.listdir(SOUNDS_DIR):
        if f.endswith('.wav'):
            size = os.path.getsize(os.path.join(SOUNDS_DIR, f))
            total += size
    print(f"Total size: {total} bytes ({total/1024:.1f} KB)")


if __name__ == "__main__":
    main()
