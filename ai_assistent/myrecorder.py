'''
import time
import sounddevice as sd
import numpy as np
import wave
import tempfile
# import matplotlib.pyplot as plt
class Recorder:
    def __init__(
        self,
        samplerate=16000,
        channels=1,
        threshold_db=-35,
        silence_timeout=1.2,   # 静音超过 1.2 秒自动停止
        min_record_time=1,   # 少于 1 秒的录音丢弃
        device=None,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.threshold_db = threshold_db
        self.silence_timeout = silence_timeout
        self.min_record_time = min_record_time
        self.device = device

        self.state = "IDLE"
        self.audio_buffer = []
        self.silence_start = None
        self.start_time = None
        self.stop_flag=False
        self.record_done = False


    def _db(self, audio_float32):
        rms = np.sqrt(np.mean(audio_float32**2))
        if rms < 1e-8:
            return -100
        return 20 * np.log10(rms)
    
    # def draw_db_plot(self):
    #     x = np.array(["DB"])
    #     y = np.array(db_values)
    #     plt.title("Real-time dB value")
    #     plt.ylim(-100, 0)
    #     plt.bar(x,y)
    #     plt.show()

    def listen_and_record(self):
        print("SmartRecorder ready...")

        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

        def callback(indata, frames, time_info, status):
            nonlocal tmp_wav

            if self.stop_flag:
                self.state = "IDLE"
                raise sd.CallbackStop()
            
            audio = indata.copy()
            db = self._db(audio)

            # ===== 状态机 =====
            if self.state == "IDLE":
                if db > self.threshold_db:
                    # 触发录音
                    self.state = "RECORDING"
                    self.start_time = time.time()
                    self.audio_buffer = [audio]
                    self.silence_start = None
                    print("RECORD START")

            elif self.state == "RECORDING":
                self.audio_buffer.append(audio)

                if db < self.threshold_db:
                    self.state = "STOPPING"
                    self.silence_start = time.time()

            elif self.state == "STOPPING":
                self.audio_buffer.append(audio)

                if db > self.threshold_db:
                    # 噪声回升 → 继续录音
                    self.state = "RECORDING"
                    self.silence_start = None
                else:
                    # 静音持续
                    if time.time() - self.silence_start > self.silence_timeout:
                        self.record_done = True
                        # 停止录音
                        self.state = "IDLE"
                        raise sd.CallbackStop()

        # determine sounddevice device index if a device spec was provided
        sd_device = None
        if self.device is not None:
            try:
                if isinstance(self.device, int):
                    sd_device = self.device
                else:
                    devices = sd.query_devices()
                    for i, d in enumerate(devices):
                        name = d.get('name', '').lower()
                        if str(self.device).lower() in name:
                            sd_device = i
                            break
            except Exception:
                sd_device = None

        with sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype='float32',
            callback=callback,
            device=sd_device
        ):
            while not self.record_done and not self.stop_flag:
                print("state:", self.state, end='\r')
                time.sleep(0.05)

        # ===== 保存 WAV =====
        if not self.audio_buffer:
            return None

        end_time = time.time()
        duration = end_time - self.start_time

        if duration < self.min_record_time:
            print("too short")
            return None

        audio_np = np.concatenate(self.audio_buffer, axis=0)
        audio_int16 = (audio_np * 32767).astype(np.int16)

        with wave.open(tmp_wav.name, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_int16.tobytes())

        print(f"录音完成: {tmp_wav.name}, 时长: {duration:.2f}s")
        self.reset()
        return tmp_wav.name
    
    def stop(self):
        self.stop_flag = True
    
    def reset(self):
        print("Recorder reset.")
        self.stop_flag = False
        self.state = "IDLE"
        self.audio_buffer = []
        self.silence_start = None
        self.start_time = None
        self.record_done = False

# recorder = Recorder()
# while True:
#     # print("Starting recording...")
#     # recorder.reset()
#     audio_path = recorder.listen_and_record()
    # if audio_path:
    #     # print("Recorded audio saved at:", audio_path)
    # else:
    #     # print("No audio recorded.")
    '''
import time
import sounddevice as sd
import numpy as np
import wave
import tempfile


class Recorder:
    def __init__(
        self,
        samplerate=16000,
        channels=1,
        threshold_db=-35,
        silence_timeout=1.8,      # 静音超过 1.8 秒自动停止
        min_record_time=0.8,      # 少于 0.8 秒的录音丢弃
        max_record_time=12.0,     # 最长录音时间，防止一直录
        device=None,
    ):
        self.samplerate = samplerate
        self.channels = channels

        # 双阈值迟滞：
        # 声音大于 start_threshold_db 才开始录音
        # 声音小于 stop_threshold_db 才认为进入静音
        self.start_threshold_db = threshold_db
        self.stop_threshold_db = threshold_db - 7

        self.silence_timeout = silence_timeout
        self.min_record_time = min_record_time
        self.max_record_time = max_record_time
        self.device = device

        self.state = "IDLE"
        self.audio_buffer = []
        self.silence_start = None
        self.start_time = None
        self.stop_flag = False
        self.record_done = False

        # 一阶高通滤波参数
        self.prev_x = 0.0
        self.prev_y = 0.0
        self.hp_alpha = 0.97

        # dB 平滑参数
        self.smooth_db = -100.0
        self.db_alpha = 0.8

    def _db(self, audio_float32):
        """
        计算当前音频帧的 dB。
        audio_float32 范围一般是 [-1, 1]。
        """
        rms = np.sqrt(np.mean(audio_float32 ** 2))
        if rms < 1e-8:
            return -100.0
        return 20 * np.log10(rms)

    def _highpass_filter(self, audio):
        """
        一阶高通滤波，削弱低频噪声。
        输入 audio shape: [frames, channels]
        """
        y = np.zeros_like(audio)

        # 当前项目一般是单声道，如果 channels=1，这样写最直接
        for i in range(len(audio)):
            x = audio[i, 0]
            y[i, 0] = self.hp_alpha * (self.prev_y + x - self.prev_x)
            self.prev_x = x
            self.prev_y = y[i, 0]

        return y

    def _smooth_db_value(self, db):
        """
        指数滑动平均，避免 dB 瞬间跳变导致状态抖动。
        db_alpha 越大越稳，但反应越慢。
        """
        self.smooth_db = self.db_alpha * self.smooth_db + (1 - self.db_alpha) * db
        return self.smooth_db

    def _resolve_sounddevice_device(self):
        """
        把传进来的 device 尝试转换成 sounddevice 可用的设备索引。
        如果传的是 int，直接用。
        如果传的是字符串，就在设备名里模糊匹配。
        如果找不到，返回 None，让 sounddevice 使用默认设备。
        """
        if self.device is None:
            return None

        try:
            if isinstance(self.device, int):
                return self.device

            devices = sd.query_devices()
            target = str(self.device).lower()

            for i, d in enumerate(devices):
                name = d.get("name", "").lower()
                if target in name:
                    return i

        except Exception as e:
            print("音频设备解析失败，使用默认输入设备:", e)

        return None

    def listen_and_record(self):
        print("SmartRecorder ready...")

        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

        def callback(indata, frames, time_info, status):
            if status:
                print("InputStream status:", status)

            if self.stop_flag:
                self.state = "IDLE"
                raise sd.CallbackStop()

            raw_audio = indata.copy()

            # 1. 先高通滤波，削弱低频噪声
            audio = self._highpass_filter(raw_audio)

            # 2. 再计算 dB
            db = self._db(audio)

            # 3. 再对 dB 做平滑
            db = self._smooth_db_value(db)

            now = time.time()

            # ===== 状态机 =====
            if self.state == "IDLE":
                if db > self.start_threshold_db:
                    self.state = "RECORDING"
                    self.start_time = now
                    self.audio_buffer = [audio]
                    self.silence_start = None
                    print("RECORD START")

            elif self.state == "RECORDING":
                self.audio_buffer.append(audio)

                # 最长录音保护
                if self.start_time is not None:
                    if now - self.start_time > self.max_record_time:
                        print("MAX RECORD TIME REACHED")
                        self.record_done = True
                        self.state = "IDLE"
                        raise sd.CallbackStop()

                # 低于停止阈值，才进入 STOPPING
                if db < self.stop_threshold_db:
                    self.state = "STOPPING"
                    self.silence_start = now

            elif self.state == "STOPPING":
                self.audio_buffer.append(audio)

                # 如果声音重新超过开始阈值，说明用户还在说话
                if db > self.start_threshold_db:
                    self.state = "RECORDING"
                    self.silence_start = None
                else:
                    # 静音持续超过 silence_timeout，结束录音
                    if self.silence_start is not None:
                        if now - self.silence_start > self.silence_timeout:
                            self.record_done = True
                            self.state = "IDLE"
                            raise sd.CallbackStop()

        sd_device = self._resolve_sounddevice_device()

        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="float32",
                callback=callback,
                device=sd_device,
            ):
                while not self.record_done and not self.stop_flag:
                    print(
                        f"state: {self.state} | db: {self.smooth_db:.1f} dB",
                        end="\r"
                    )
                    time.sleep(0.05)

        except Exception as e:
            print("录音异常:", e)
            self.reset()
            return None

        # ===== 保存 WAV =====
        if not self.audio_buffer:
            self.reset()
            return None

        if self.start_time is None:
            self.reset()
            return None

        end_time = time.time()
        duration = end_time - self.start_time

        if duration < self.min_record_time:
            print("too short")
            self.reset()
            return None

        audio_np = np.concatenate(self.audio_buffer, axis=0)

        # 防止数值超过 [-1, 1]，避免转 int16 时爆音
        audio_np = np.clip(audio_np, -1.0, 1.0)

        audio_int16 = (audio_np * 32767).astype(np.int16)

        with wave.open(tmp_wav.name, "w") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio_int16.tobytes())

        print(f"\n录音完成: {tmp_wav.name}, 时长: {duration:.2f}s")

        self.reset()
        return tmp_wav.name

    def stop(self):
        self.stop_flag = True

    def reset(self):
        print("Recorder reset.")
        self.stop_flag = False
        self.state = "IDLE"
        self.audio_buffer = []
        self.silence_start = None
        self.start_time = None
        self.record_done = False

        # 重置滤波和平滑状态
        self.prev_x = 0.0
        self.prev_y = 0.0
        self.smooth_db = -100.0


# 单独测试用
if __name__ == "__main__":
    recorder = Recorder(
        samplerate=16000,
        channels=1,
        threshold_db=-35,
        silence_timeout=1.8,
        min_record_time=0.8,
        max_record_time=12.0,
        device=None,
    )

    while True:
        audio_path = recorder.listen_and_record()
        if audio_path:
            print("Recorded audio saved at:", audio_path)
        else:
            print("No audio recorded.")