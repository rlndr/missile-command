"""Retro sound effects synthesised in code.

Every sound is built procedurally from square-wave pitch sweeps and LFSR
noise bursts with simple linear envelopes. No audio files or sample tables
are used. When there is no audio device or mixer the game runs silently.
"""

import functools
from array import array

import pygame

from game.constants import *

_MIXER_ERRORS = (pygame.error, NotImplementedError, ImportError)

# Recipe per sound name: (generator, constant arguments).
_SWEEP = "sweep"
_NOISE = "noise"
_TICK_TOCK = "tick_tock"
_RECIPES = {
    "launch": (_SWEEP, SOUND_LAUNCH_SWEEP),
    "explosion": (_NOISE, SOUND_EXPLOSION_NOISE),
    "intercept": (_SWEEP, SOUND_INTERCEPT_SWEEP),
    "impact": (_NOISE, SOUND_IMPACT_NOISE),
    "game_over": (_SWEEP, SOUND_GAME_OVER_SWEEP),
    "laser": (_SWEEP, SOUND_LASER_SWEEP),
    "tick_tock": (_TICK_TOCK, SOUND_TICK_TOCK),
}


def _peak(volume):
    """Return the peak 16-bit amplitude for ``volume`` (0.0 to 1.0)."""
    return round(volume * 32767)


def square_sweep(start_hz, end_hz, duration, sample_rate=SOUND_SAMPLE_RATE,
                 volume=SOUND_VOLUME):
    """Return a square wave sweeping linearly from ``start_hz`` to ``end_hz``.

    The result is an ``array('h')`` of ``round(duration * sample_rate)`` mono
    signed 16-bit samples. Phase is accumulated per sample so the sweep never
    jumps. Amplitude is the full peak until the last ``SOUND_FADE_TIME``
    seconds, which fade linearly so the last sample is exactly 0.
    """
    n = round(duration * sample_rate)
    peak = _peak(volume)
    fade = min(n, round(SOUND_FADE_TIME * sample_rate))
    fade_start = n - fade
    samples = array('h', bytes(2 * n))
    phase = 0.0
    span = end_hz - start_hz
    for i in range(n):
        if i < fade_start:
            amp = peak
        else:
            amp = round(peak * (n - 1 - i) / fade)
        samples[i] = amp if phase < 0.5 else -amp
        freq = start_hz + span * i / n
        phase += freq / sample_rate
        phase -= int(phase)
    return samples


def noise_burst(step_hz, duration, sample_rate=SOUND_SAMPLE_RATE,
                volume=SOUND_VOLUME, seed=SOUND_NOISE_SEED):
    """Return a decaying burst of square noise from a 15-bit LFSR.

    The register starts at ``seed`` (must be non-zero) and steps
    ``step_hz`` times per second, so each pseudo-random bit is held for
    about ``sample_rate / step_hz`` samples as ``+A`` or ``-A``. The
    envelope falls linearly from the peak at sample 0 to exactly 0 at the
    last sample. The output depends only on the arguments.
    """
    lfsr = seed & 0x7FFF
    if lfsr == 0:
        raise ValueError("noise seed must be non-zero in its low 15 bits")
    n = round(duration * sample_rate)
    peak = _peak(volume)
    samples = array('h', bytes(2 * n))
    step = step_hz / sample_rate
    acc = 0.0
    last = max(n - 1, 1)
    for i in range(n):
        amp = round(peak * (n - 1 - i) / last)
        samples[i] = amp if lfsr & 1 else -amp
        acc += step
        while acc >= 1.0:
            acc -= 1.0
            # Taps at bits 0 and 1 (x^15 + x^14 + 1), a maximal-length register.
            bit = (lfsr ^ (lfsr >> 1)) & 1
            lfsr = (lfsr >> 1) | (bit << 14)
    return samples


def tick_tock(tick_hz, tock_hz, tick_duration, gap_duration, tock_duration,
              sample_rate=SOUND_SAMPLE_RATE, volume=SOUND_VOLUME):
    """Return a two-tone ``tick`` + silent ``gap`` + ``tock`` square-wave cue.

    Both tones use ``square_sweep`` at constant frequency so each segment fades
    cleanly to 0 over its final ``SOUND_FADE_TIME`` seconds. The result is a
    mono ``array('h')`` of ``round(tick_duration * sample_rate) +
    round(gap_duration * sample_rate) + round(tock_duration * sample_rate)``
    signed 16-bit samples.
    """
    tick = square_sweep(tick_hz, tick_hz, tick_duration, sample_rate, volume)
    gap = array('h', bytes(2 * round(gap_duration * sample_rate)))
    tock = square_sweep(tock_hz, tock_hz, tock_duration, sample_rate, volume)
    return tick + gap + tock


@functools.lru_cache(maxsize=None)
def sound_bytes(name, sample_rate, channels):
    """Return the raw signed 16-bit mixer buffer for sound ``name``.

    Each mono sample is repeated ``channels`` times to interleave the
    channels. Results are cached per ``(name, sample_rate, channels)``.
    Raises ``KeyError`` for a name not in ``SOUND_NAMES``.
    """
    kind, args = _RECIPES[name]
    if kind == _SWEEP:
        start_hz, end_hz, duration = args
        mono = square_sweep(start_hz, end_hz, duration, sample_rate)
    elif kind == _TICK_TOCK:
        mono = tick_tock(*args, sample_rate)
    else:
        step_hz, duration = args
        mono = noise_burst(step_hz, duration, sample_rate)
    if channels == 1:
        return mono.tobytes()
    interleaved = array('h', (x for x in mono for _ in range(channels)))
    return interleaved.tobytes()


def pre_init_mixer():
    """Ask pygame for a small mono 16-bit mixer before ``pygame.init()``.

    Never raises for a missing or broken mixer.
    """
    try:
        pygame.mixer.pre_init(SOUND_SAMPLE_RATE, -16, 1, SOUND_BUFFER_SIZE)
    except _MIXER_ERRORS:
        pass


class SoundSystem:
    """Builds the game's sound effects and plays them on request.

    ``available`` is False when there is no usable mixer; then ``play()``
    does nothing. ``muted`` silences playback without unloading sounds.
    """

    def __init__(self):
        """Open the mixer if needed and build one ``Sound`` per name."""
        self.sounds = {}
        self.available = False
        self.muted = False
        try:
            mixer = pygame.mixer
            if mixer.get_init() is None:
                mixer.init(SOUND_SAMPLE_RATE, -16, 1, SOUND_BUFFER_SIZE)
            init = mixer.get_init()
            if init is not None:
                freq, size, channels = init
                if size == -16:
                    sounds = {}
                    for name in SOUND_NAMES:
                        sounds[name] = mixer.Sound(
                            buffer=sound_bytes(name, freq, channels))
                    self.sounds = sounds
                    self.available = True
        except _MIXER_ERRORS:
            self.sounds = {}
            self.available = False

    def play(self, name):
        """Play sound ``name``; return True if it was started.

        Raises ``KeyError`` for an unknown name even without audio. Returns
        False when muted, unavailable, or if the mixer has been shut down
        (for example by ``pygame.quit()``). pygame 2.6 crashes instead of
        raising when a ``Sound`` is played on a closed mixer, so that case
        is checked with ``get_init()`` before playing.
        """
        if name not in SOUND_NAMES:
            raise KeyError(name)
        if self.muted or not self.available:
            return False
        try:
            if pygame.mixer.get_init() is None:
                return False
            self.sounds[name].play()
        except _MIXER_ERRORS:
            return False
        return True

    def toggle_mute(self):
        """Flip ``muted`` and return the new value."""
        self.muted = not self.muted
        return self.muted
