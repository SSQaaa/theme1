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