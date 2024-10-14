import sys
import os
import requests
import keyboard
import pyaudio
import threading
import wave
import api_config
import character_config
import json
from PyQt5.QtWidgets import QApplication
import time

class SpeechToTextConverter:
    def __init__(self, client_id, client_secret, home_directory, get_stt_sleep_term=0.25, is_debug=False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.home_directory = home_directory; os.makedirs(self.home_directory, exist_ok=True)
        self.is_debug = is_debug
        self.get_stt_sleep_term = get_stt_sleep_term

        self.token = None
        self.token_expiration = None
        self.recording = False
        self.stream = None
        self.audio_data = bytearray()
        self.pyaudio_instance = pyaudio.PyAudio()

        self.user_stt_text = ""

        # 오디오 설정
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024

        # 단축키 등록
        keyboard.add_hotkey('ctrl+f12', self.toggle_recording)
        threading.Thread(target=self.token_scheduler).start()

    def get_user_stt_text(self):
        if self.user_stt_text != "":
            return_text = self.user_stt_text
            self.user_stt_text = ""
            return return_text
        return self.user_stt_text

    def token_scheduler(self):
        start_time = time.time()  # 시작 시간 저장
        self.refresh_token()

        while True:
            current_time = time.time()  # 현재 시간 저장
            elapsed_time = current_time - start_time  # 경과 시간 계산

            if elapsed_time >= 3600:  # 3600초(1시간) 이상 경과한 경우
                self.refresh_token()
                start_time = current_time  # 시작 시간 갱신
            else:
                time.sleep(1)  # 1초 동안 대기

    def refresh_token(self):
        response = requests.post(
            'https://openapi.vito.ai/v1/authenticate',
            data={'client_id': self.client_id, 'client_secret': self.client_secret}
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            self.token_expiration = data['expire_at']
            if self.is_debug:
                print("Token refreshed successfully")
        else:
            print("Error refreshing token:", response.status_code)

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recording = True
        self.stream = self.pyaudio_instance.open(format=self.format, channels=self.channels,
                                                rate=self.rate, input=True, frames_per_buffer=self.chunk)
        self.audio_data = bytearray()
        threading.Thread(target=self.record).start()

    def record(self):
        while self.recording:
            data = self.stream.read(self.chunk)
            self.audio_data.extend(data)

    def stop_recording(self):
        self.recording = False
        self.stream.stop_stream()
        self.stream.close()
        self.send_audio_data()

    def send_audio_data(self):
        # 파일 저장 (임시)
        filename = os.path.join(self.home_directory, "user_recording.wav")
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(self.audio_data)
        wf.close()

        # API 요청
        config = {
            "use_diarization": True,
            "diarization": {
                "spk_count": 1
            },
            "use_multi_channel": False,
            "use_itn": False,
            "use_disfluency_filter": False,
            "use_profanity_filter": False,
            "use_paragraph_splitter": True,
            "paragraph_splitter": {
                "max": 50
            },
            "keywords": ["안녕"]
        }

        if self.token is None:
            raise print("There is no token")

        resp = requests.post(
            'https://openapi.vito.ai/v1/transcribe',
            headers={'Authorization': 'bearer ' + self.token},
            data={'config': json.dumps(config)},
            files={'file': open(filename, 'rb')}
        )
        resp.raise_for_status()
        if self.is_debug:
            print(resp.json())

        if resp.status_code == 200:
            # print("Transcription Successful")
            resp_json = resp.json()
            headers = {'Authorization': 'Bearer ' + self.token}
            response = requests.get(f'https://openapi.vito.ai/v1/transcribe/{resp_json["id"]}', headers=headers)
            self.process_response(response.json())
        else:
            raise print("Error in Transcription STT Module: ", resp.status_code)

    def process_response(self, response):
        transcribe_id = response.get('id', '')
        status = response.get('status', '')

        if status == 'completed':
            results = response.get('results', {}).get('utterances', [])
            for utterance in results:
                start_at = utterance.get('start_at')
                duration = utterance.get('duration')
                msg = utterance.get('msg')
                spk = utterance.get('spk')
                if self.is_debug:
                    print(f"Start at: {start_at} ms, Duration: {duration} ms, Speaker: {spk}, Message: {msg}")
                self.user_stt_text = msg

        elif status == 'transcribing':
            # 폴링 메커니즘 구현
            self.poll_transcription_status(transcribe_id)
        elif status == 'failed':
            print(f"Transcription failed for ID: {transcribe_id}")

    def poll_transcription_status(self, transcribe_id):
        while True:
            time.sleep(self.get_stt_sleep_term)
            response = self.check_transcription_status(transcribe_id)
            if response.get('status') in ['completed', 'failed']:
                self.process_response(response)
                break

    def check_transcription_status(self, transcribe_id):
        headers = {'Authorization': 'Bearer ' + self.token}
        response = requests.get(f'https://openapi.vito.ai/v1/transcribe/{transcribe_id}', headers=headers)
        return response.json()

if __name__ == "__main__":
    # app = QApplication(sys.argv)
    project_folder_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "MYS_PROJECT", character_config.CHARACTER_NAME)
    STT_converter = SpeechToTextConverter(client_id=api_config.RETURN_ZERO_CLIENT_ID,
                                          client_secret=api_config.RETURN_ZERO_API_KEY,
                                          home_directory=project_folder_dir)
    # STT_converter.run()

    while True:
        QApplication.processEvents()  # PyQT 이벤트 루프 유지
        stt_user_text = STT_converter.get_user_stt_text()
        if stt_user_text != "":
            print(stt_user_text)