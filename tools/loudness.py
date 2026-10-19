"""ITU-R BS.1770 방식 체감 음량(LUFS) - 짧은 대사용 (400ms 블록, 75% 겹침, -70 LUFS 절대 게이트 + 상대 게이트)"""
import numpy as np
from scipy.signal import lfilter


def _k_filter(x, sr):
    # 1단: 고역 선반 필터 (+4dB, 약 1.5kHz), 2단: 고역 통과 (약 38Hz) - BS.1770 계수를 sr에 맞춰 설계
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / sr)
    b2 = [1, -2, 1]
    a2 = [1, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)]
    return lfilter(b2, a2, lfilter(b1, a1, x))


def lufs(x, sr):
    y = _k_filter(np.asarray(x, np.float64) / 32768.0, sr)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(y) < blk:
        y = np.pad(y, (0, blk - len(y)))
    ms = np.array([np.mean(y[i:i + blk] ** 2) for i in range(0, len(y) - blk + 1, hop)])
    ms = ms[-0.691 + 10 * np.log10(ms + 1e-12) > -70]
    if len(ms) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(ms.mean()) - 10
    ms = ms[-0.691 + 10 * np.log10(ms) > rel]
    return float(-0.691 + 10 * np.log10(ms.mean()))


def _peak_release(r, a):
    """env[i] = max(r[i], a·env[i-1]) (즉시 올라가고 지수로 내려오는 봉우리 추적, r ≥ 0).
    로그 영역에서 누적 최댓값으로 계산한다: env[i] = a^i · max_{j≤i} r[j]/a^j."""
    i = np.arange(len(r))
    with np.errstate(divide='ignore'):
        lr = np.log(np.maximum(r, 0.0))
    la = np.log(a)
    return np.exp(np.maximum.accumulate(lr - i * la) + i * la)


def _compress(x, sr, ratio=3.0, depth_db=12.0, attack=0.005, release=0.08):
    """RMS(10ms) 컴프레서. 가장 큰 구간보다 depth_db 아래부터 ratio:1로 누른다.
    감쇠량은 즉시 따라가고 release로 풀린 뒤, attack 시정수로 부드럽게 한다."""
    win = max(1, int(0.01 * sr))
    level = 10 * np.log10(np.convolve(x ** 2, np.ones(win) / win, 'same') + 1e-9)
    thr = level.max() - depth_db
    red = np.where(level > thr, level - (thr + (level - thr) / ratio), 0.0)      # 줄일 dB (≥ 0)
    red = _peak_release(red, np.exp(-1 / (release * sr)))
    a_att = np.exp(-1 / (attack * sr))
    red = lfilter([1 - a_att], [1, -a_att], red)
    return x * 10 ** (-red / 20)


def _limit(y, sr, ceil, look=0.002, release=0.05):
    """룩어헤드 피크 리미터: 순간 피크만 ceil 아래로 누른다 (즉시 누르고 release로 풀림)."""
    from scipy.ndimage import minimum_filter1d
    need = np.minimum(1.0, ceil / np.maximum(np.abs(y), 1e-9))
    need = minimum_filter1d(need, size=2 * int(look * sr) + 1, mode='nearest')
    g = 1.0 - _peak_release(1.0 - need, np.exp(-1 / (release * sr)))
    return np.clip(y * g, -ceil, ceil)


def master(x, sr, target_lufs, ceiling_db=-0.3):
    """게임 음성처럼 촘촘하게 눌러 목표 LUFS로 맞춘다. 피크는 ceiling_db 이하.
    원본 외침처럼 아주 큰 줄은 기본 압축으로 목표에 못 미치므로 압축을 점점 세게 건다."""
    ceil = 32768 * 10 ** (ceiling_db / 20)
    x = np.asarray(x, np.float64)
    z = _master_stages(x, sr, target_lufs, ceil)
    if lufs(z, sr) < target_lufs - 0.5:
        # 그래도 모자라면 음색 문제(2~4kHz가 약함): 고역을 4dB 올려 다시 (외침이 더 또렷해짐)
        z = _master_stages(_high_shelf(x, sr, 2000, 4.0), sr, target_lufs, ceil)
    if lufs(z, sr) < target_lufs - 0.5:
        # 원본 외침처럼 아주 큰 줄: 리미터로는 파형 봉우리가 줄지 않으므로 가볍게 새추레이션(최소한만)
        for drive in np.arange(1.0, 2.01, 0.1):
            s = ceil * np.tanh(drive * z / ceil) / np.tanh(drive)
            if lufs(s, sr) >= target_lufs - 0.3:
                break
        z = s
    return z


def _high_shelf(x, sr, f0, gain_db, q=0.707):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / sr
    alpha = np.sin(w) / (2 * q)
    cw, sa = np.cos(w), 2 * np.sqrt(A) * alpha
    b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
    a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    return lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def _master_stages(x, sr, target_lufs, ceil):
    for ratio, depth, release in ((3.0, 12.0, 0.05), (4.0, 18.0, 0.02), (6.0, 24.0, 0.008)):
        y = _compress(x, sr, ratio=ratio, depth_db=depth)
        y *= ceil / np.abs(y).max()            # 피크를 천장에 맞춘 뒤, 모자란 만큼만 리미터로 끌어올린다
        gain = max(1.0, 10 ** ((target_lufs - lufs(y, sr)) / 20))
        z = _limit(y * gain, sr, ceil, release=release)
        for _ in range(20):
            d = target_lufs - lufs(z, sr)
            if abs(d) < 0.2:
                return z
            gain = min(8.0, gain * 10 ** (d / 20))   # 리미팅 최대 18dB
            z = _limit(y * gain, sr, ceil, release=release)
    return z
