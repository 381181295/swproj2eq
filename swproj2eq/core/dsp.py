"""DSP-related shared helpers."""

import array
import math
import wave


def compute_preamp_db(channels, extra_headroom_db=1.0):
    """Return global safety preamp from max positive gain.

    Policy:
      preamp_db = -(global_max_positive_gain + extra_headroom_db)
    """
    if not channels:
        return 0.0
    max_gain = max(max(ch.correction_dB) for ch in channels)
    if max_gain <= 0:
        return 0.0
    return -(max_gain + extra_headroom_db)


def freq_response_to_ir(freqs, gains_dB, sample_rate=48000, ir_length=4096):
    """Convert frequency/gain curve to minimum-phase FIR."""
    n_fft = ir_length
    half = n_fft // 2 + 1

    bin_freqs = [i * sample_rate / n_fft for i in range(half)]
    interp_gains_dB = []
    for bf in bin_freqs:
        if bf <= freqs[0]:
            interp_gains_dB.append(gains_dB[0])
        elif bf >= freqs[-1]:
            interp_gains_dB.append(gains_dB[-1])
        else:
            lo, hi = 0, len(freqs) - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if freqs[mid] <= bf:
                    lo = mid
                else:
                    hi = mid
            if freqs[hi] != freqs[lo]:
                t = (math.log(bf) - math.log(freqs[lo])) / (
                    math.log(freqs[hi]) - math.log(freqs[lo])
                )
            else:
                t = 0
            interp_gains_dB.append(gains_dB[lo] + t * (gains_dB[hi] - gains_dB[lo]))

    magnitudes = [10 ** (g / 20.0) for g in interp_gains_dB]
    log_mag = [math.log(max(m, 1e-10)) for m in magnitudes]
    full_log_mag = log_mag + log_mag[-2:0:-1]

    n = len(full_log_mag)
    cepstrum_real = [0.0] * n
    cepstrum_imag = [0.0] * n
    for k in range(n):
        for j in range(n):
            angle = 2 * math.pi * k * j / n
            cepstrum_real[k] += full_log_mag[j] * math.cos(angle) / n
            cepstrum_imag[k] += full_log_mag[j] * (-math.sin(angle)) / n

    mp_cepstrum_real = [0.0] * n
    mp_cepstrum_imag = [0.0] * n
    mp_cepstrum_real[0] = cepstrum_real[0]
    for k in range(1, n // 2):
        mp_cepstrum_real[k] = 2 * cepstrum_real[k]
        mp_cepstrum_imag[k] = 2 * cepstrum_imag[k]
    if n % 2 == 0:
        mp_cepstrum_real[n // 2] = cepstrum_real[n // 2]

    spec_real = [0.0] * n
    spec_imag = [0.0] * n
    for k in range(n):
        for j in range(n):
            angle = 2 * math.pi * k * j / n
            spec_real[k] += mp_cepstrum_real[j] * math.cos(angle) - mp_cepstrum_imag[j] * (
                -math.sin(angle)
            )
            spec_imag[k] += mp_cepstrum_real[j] * (-math.sin(angle)) + mp_cepstrum_imag[j] * math.cos(
                angle
            )

    mp_spec_real = [0.0] * n
    mp_spec_imag = [0.0] * n
    for k in range(n):
        e_real = math.exp(spec_real[k])
        mp_spec_real[k] = e_real * math.cos(spec_imag[k])
        mp_spec_imag[k] = e_real * math.sin(spec_imag[k])

    ir = [0.0] * n
    for k in range(n):
        for j in range(n):
            angle = 2 * math.pi * k * j / n
            ir[k] += mp_spec_real[j] * math.cos(angle) - mp_spec_imag[j] * (-math.sin(angle))
        ir[k] /= n

    return ir[:ir_length]


def freq_response_to_ir_fast(freqs, gains_dB, sample_rate=48000, ir_length=4096):
    """Fast path using numpy if available."""
    try:
        import numpy as np

        n_fft = ir_length
        half = n_fft // 2 + 1
        bin_freqs = np.linspace(0, sample_rate / 2, half)
        interp_gains = np.interp(
            np.log(np.clip(bin_freqs, freqs[0], freqs[-1])),
            np.log(freqs),
            gains_dB,
        )
        interp_gains[bin_freqs < freqs[0]] = gains_dB[0]
        interp_gains[bin_freqs > freqs[-1]] = gains_dB[-1]

        magnitudes = 10 ** (interp_gains / 20.0)
        log_mag = np.log(np.clip(magnitudes, 1e-10, None))
        full_log_mag = np.concatenate([log_mag, log_mag[-2:0:-1]])
        cepstrum = np.fft.ifft(full_log_mag).real

        n = len(cepstrum)
        window = np.zeros(n)
        window[0] = 1
        window[1 : n // 2] = 2
        if n % 2 == 0:
            window[n // 2] = 1
        mp_cepstrum = cepstrum * window
        min_phase_spec = np.exp(np.fft.fft(mp_cepstrum))
        ir = np.fft.ifft(min_phase_spec).real
        return ir[:ir_length].tolist()
    except ImportError:
        return freq_response_to_ir(freqs, gains_dB, sample_rate, ir_length)


def write_wav(filepath, samples, sample_rate=48000):
    """Write mono IR as 16-bit WAV."""
    peak = max(abs(s) for s in samples) or 1.0
    scale = 0.95 / peak
    int_samples = [max(-32767, min(32767, int(s * scale * 32767))) for s in samples]
    with wave.open(filepath, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(array.array("h", int_samples).tobytes())
