import numpy as np
import sounddevice as sd
import time
import math

class AudioDBMonitor:
    def __init__(self, samplerate=16000, blocksize=1024, channels=1):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.channels = channels

    def _rms(self, audio):
        """均方根"""
        return np.sqrt(np.mean(np.square(audio)))

    def _dbfs(self, rms):
        """转换为分贝（dBFS）"""
        if rms <= 1e-9:
            return -100.0
        return 20 * math.log10(rms)

    def get_db_level(self, duration=0.5):
        """
        读取一小段音频并计算分贝
        :param duration: 采样时长（秒）
        """
        frames = int(self.samplerate * duration)
        audio = sd.rec(frames, samplerate=self.samplerate, channels=self.channels, dtype='float32')
        sd.wait()
        audio = audio.flatten()
        rms = self._rms(audio)
        db = self._dbfs(rms)
        return db

    def is_loud(self, threshold_db=-40):
        """
        是否超过阈值
        """
        db = self.get_db_level()
        return db > threshold_db

    def wait_for_sound(self, threshold_db=-40, timeout=None):
        """
        阻塞等待声音触发
        :param threshold_db: 分贝阈值
        :param timeout: 超时秒（None = 一直等）
        """
        start = time.time()
        while True:
            db = self.get_db_level(duration=0.2)
            if db > threshold_db:
                return True, db

            if timeout is not None and (time.time() - start) > timeout:
                return False, db
