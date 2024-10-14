import requests
import api_config
import character_config

class DeepLTranslator:
    def __init__(self, auth_key, target_language, api_url='https://api-free.deepl.com/v2/translate', is_debug=False):
        self.auth_key = auth_key
        self.api_url = api_url
        self.deepl_translation_language = self.get_target_language(target_language)
        self.last_translation_result = ""
        self.is_debug = is_debug

    def get_target_language(self, target_language):
        if target_language == "english":
            return "EN"
        elif target_language == "korean":
            return "KO"
        elif target_language == "japanese":
            return "JA"
        else:
            raise ValueError("Unsupported language")

    def translate(self, text):
        headers = {
            'Authorization': f'DeepL-Auth-Key {self.auth_key}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = {
            'text': text,
            'target_lang': self.deepl_translation_language,
        }

        response = requests.post(self.api_url, headers=headers, data=data)

        if response.status_code == 200:
            translation_data = response.json()
            translated_text = translation_data['translations'][0]['text']
            self.last_translation_result = translated_text
            if self.is_debug:
                print(f"DeepL Translation Result : {self.last_translation_result}")
            return translated_text
        else:
            print(response.text)
            self.last_translation_result = ""
            raise print(f'API 요청 실패: {response.status_code}')

if __name__ == '__main__':

    # DeepLTranslator 클래스 인스턴스 생성
    translator = DeepLTranslator(auth_key=api_config.DEEPL_API_KEY, target_language=character_config.TRANSLATION_LANGUAGE)

    # 번역 테스트
    print(translator.translate("昨夜のセックスは…やはり、アドミンの欲望を満たすための苦しい快楽でした。"))


    # api-free.deepl.com
    # API KEY b7767612-b73d-77ea-686a-71283f48d9de:fx