import requests
import threading
import api_config
import character_config
import os
import datetime
import pyaudio
import wave

class TextToSpeechConverter:
    def __init__(self, api_url, speech_language, character_config, home_directory,
                 noise_scale=0.6, noise_scale_w=0.668, length_scale=1.0, speaker_id=0, is_debug=False):
        self.api_url = api_url
        self.home_directory = home_directory; os.makedirs(self.home_directory, exist_ok=True)
        self.speech_language = speech_language
        self.character_config = character_config
        self.is_debug = is_debug

        if self.speech_language == "japanese":
            self.speech_language = "[JA]"
        elif self.speech_language == "korean":
            self.speech_language = "[KR]"
        else:
            raise print(f"Unsupported Language : {self.speech_language}")

    def send_request(self, input_string):

        if self.is_debug:
            print(f"TTS Module Received input_string : {input_string}")

        data = self.character_config.copy()
        data["text"] = f"{input_string}"

        # POST 요청을 통해 파일 받기
        response = requests.post(self.api_url, json=data)
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y%m%d_%H%M%S%f")[:-3]

        # 응답이 성공적인 경우
        if response.status_code == 200:
            # 받은 파일을 로컬 시스템에 저장
            save_path = os.path.join(self.home_directory, f'{formatted_time}_character_voice.wav')
            with open(save_path, 'wb') as f:
                f.write(response.content)
            if self.is_debug:
                print(f"File saved as '{save_path}'")
            return save_path
        else:
            if self.is_debug:
                print(f"Failed to retrieve file. Status code: {response.status_code}")
            return ""

    def play_character_sound(self, file_path, must_play_sound=False): # TODO : Thread

        if file_path == "" and must_play_sound:
            raise print("Not Supported Voice!")
        elif file_path == "":
            return

        # WAV 파일 열기
        wf = wave.open(file_path, 'rb')

        # PyAudio 스트림 초기화
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # 데이터 청크를 읽고 재생
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)

        # 스트림 정리
        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    # FastAPI 서버의 URL

    character_config_list = api_config.CHARACTER_API_CONFIG_DICT[character_config.CHARACTER_NAME]
    # api_url = f'http://ms-ms-vpnclient01.iptime.org:7860/{character_config.CHARACTER_NAME}'
    project_folder_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "MYS_PROJECT",
                                      character_config.CHARACTER_NAME)


    tts_api = TextToSpeechConverter(api_url=character_config_list[1], speech_language="korean",
                                    character_config=character_config_list[0], home_directory=project_folder_dir)
    tts_api.play_character_sound(tts_api.send_request("아아 안녕하세요~"))

    # TTSAPI 클래스의 인스턴스 생성
    tts_api = TextToSpeechConverter(api_url=character_config_list[1], speech_language="japanese",
                                    character_config=character_config_list[0], home_directory=project_folder_dir)

    # 요청 보내기
    # tts_api.play_character_sound(tts_api.send_request("ありす、パーティーに合流します。"))
    # tts_api.play_character_sound(tts_api.send_request("せ、せ、先生！ 何言ってるんですか！？"))
    tts_api.play_character_sound(tts_api.send_request("くふふ～。照れる表情、面白～い"))
    # print(tts_api.send_request("ありす、パーティーに合流します。"))

    # tts_api.play_character_sound(tts_api.send_request("はっ！？な、なんでそんなこと言うのよ！\
    #                                                    私にとってあなたなんてただの迷惑な存在よ。\
    #                                                    それに、私はあんな気持ちになんてならないわ！だから...そ、それ以降は黙っててくれなさい！"))
    # tts_api.play_character_sound(tts_api.send_request("え、そ、そんなことは…！別に私は何も期待していないわよ！ただ、あなたがそんなことをしてくれるなんて意外だったわ…た、確かに素直に感謝するわ！ありがとう、バカ！"))
