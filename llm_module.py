from openai import OpenAI
import os
import character_config
import api_config
import re

os.environ["OPENAI_API_KEY"] = f"{api_config.OPENAI_API_KEY}"

client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class OpenaiChatApi():
    def __init__(self, character_prompt, target_model="gpt-3.5-turbo-16k-0613", conversation_language="japanese", translation_language="korean",
                 conversation_history="", character_first_saying="", sub_prompt="", is_debug=False):
        self.model = target_model  # The model you want to use
        self.character_prompt = character_prompt
        self.conversation_language = conversation_language
        self.translation_language = translation_language
        self.conversation_history = conversation_history
        self.character_first_saying = character_first_saying
        self.sub_prompt = sub_prompt
        self.is_debug = is_debug

        self.prompt_config = {
              "temperature": 0.8,
              "max_tokens": 600,
              "presence_penalty": 0.5,
              "frequency_penalty": 0.2,
              "stream": False,
              "top_p": 1
        }

        self.user_conversation_list = []
        self.character_conversation_list = []

    def get_example_each_language(self, input_language):
        if input_language == "english":
            return "Good morning"  # 띄어쓰기 및 일부 문장 부호 포함
        elif input_language == "korean":
            return "좋은 아침이에요"
        elif input_language == "japanese":
            return "おはようございます"
        else:
            raise ValueError("Unsupported language")

    def send_my_message(self, user_input):

        # conversation_lang_example, translation_lang_example = \
        #     self.get_example_each_language(self.conversation_language), self.get_example_each_language(self.translation_language)

        prompt = self.character_prompt
        # prompt += "" if self.conversation_history == "" else f"\n\n{self.conversation_history}\n" + "Above is the conversation history. Please keep this in mind when communicating with user. \n"
        # prompt += f"Please be careful not to mention [Character Name:] when talking. \n"
        # prompt += f"You respond exclusively in One sentence, {self.conversation_language} and {self.translation_language}. Last sentence is translated from {self.conversation_language} to {self.translation_language} taking advantage of the character's personality. Please translate so that it is as similar to the original context as possible. "
        # prompt += f"Each sentence is separated by '#' symbol. For example, {conversation_lang_example}#{translation_lang_example}. You exclusively response in [{self.conversation_language}]&[{self.translation_language}], Without any other language. "
                  # She will respond exclusively in {self.conversation_language}, without any phonetic readings, regardless of the input language."

        messages = []
        messages.append({"role": "system", "content": f"{prompt}"})
        if self.character_first_saying != "" and self.conversation_history == "":
            messages.append({"role": "assistant", "content": f"{self.character_first_saying}"})
        for user_conversation, character_conversation in zip(self.user_conversation_list, self.character_conversation_list):
            messages.append({"role": "user", "content": f"{user_conversation}"})
            messages.append({"role": "assistant", "content": f"{character_conversation}"})
        if self.sub_prompt != "":
            messages.append({"role": "system", "content": self.sub_prompt})
        messages.append({"role": "user", "content": f"{user_input}"})

        while True:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                **self.prompt_config
            )
            character_response = response.choices[0].message.content.strip().replace("\n\n", "\n")

            # character_said, character_translated = self.split_with_two_lines(character_response)
            #
            # if self.is_single_language_string(character_said, self.conversation_language) and \
            #         self.is_single_language_string(character_translated, self.translation_language):
            #     break
            # else:
            #     user_input = f"You exclusively response in [{self.conversation_language}]&[{self.translation_language}], For example, {conversation_lang_example}#{translation_lang_example}.\n\n" + user_input
            #     print("캐릭터가 다른 언어로 말하였습니다. 다시 시도합니다.")
            #     print(f"{character_said} & {character_translated}")

            if self.is_single_language_string(character_response, self.translation_language):
                break
            else:
                print("캐릭터가 다른 언어로 말하였습니다. 다시 시도합니다.")
                print(character_response)

        if self.is_debug:
            print(f"{character_config.CHARACTER_NAME}:", character_response)

        self.user_conversation_list.append(user_input)
        self.character_conversation_list.append(character_response)

        # self.conversation_history += f"User: {user_input}\n{character_config.CHARACTER_NAME}: {character_response}\n"

        return self.split_character_emotion_and_conversation(character_response)

    def is_single_language_string(self, input_string, language):
        if language == "english":
            pattern = r'[A-Za-z\s\.,!?\'"]'  # 띄어쓰기 및 일부 문장 부호 포함
        elif language == "korean":
            pattern = r'[가-힣\s\.,!?\'"]'  # 띄어쓰기 및 일부 문장 부호 포함
        elif language == "japanese":
            pattern = r'[ぁ-んァ-ンー一-龠\s、。!?\'"]'  # 띄어쓰기 및 일본어 문장 부호 포함
        else:
            raise ValueError("Unsupported language")

        # 입력 문자열에서 해당 언어 문자를 찾아내어 그 길이를 계산
        matched_chars = re.findall(pattern, input_string)
        matched_length = len(''.join(matched_chars))

        # 나머지 문자열의 길이가 입력 문자열의 절반 이상인 경우 True 반환
        return (matched_length / len(input_string)) >= 0.5

    def split_character_emotion_and_conversation(self, character_response_original):

        character_response = character_response_original

        # 쌍따옴표로 묶인 문자열을 추출합니다.
        double_quoted_strings = re.findall(r'"([^"]*)"', character_response_original)

        # 괄호로 묶인 문자열을 추출합니다.
        parenthesized_strings = re.findall(r'\(([^)]*)\)', character_response_original)

        # 쌍따옴표로 묶인 문자열을 공백으로 구분하여 결합
        double_quoted_combined = ' '.join(double_quoted_strings)

        # 괄호로 묶인 문자열을 공백으로 구분하여 결합
        parenthesized_combined = ' '.join(parenthesized_strings)

        if self.is_debug:
            print(f"character_saying in gpt_module : {double_quoted_combined}")
            print(f"whole saying in gpt_module : {character_response}")
            # print(parenthesized_combined + "\n" + double_quoted_combined + "\n" + character_response)

        return parenthesized_combined, double_quoted_combined, character_response_original

        # temp_character_response = character_response.replace("\n", "")
        # index = temp_character_response.find(")")
        #
        # if index == -1:
        #     return "", character_response  # emotion, conversation
        # else:
        #     return temp_character_response[:index+1], temp_character_response[index+1:], character_response # emotion, conversation

    # def split_with_two_lines(self, character_response):
    #     temp_response = character_response.replace("\n", "#")
    #     character_said, character_translated = temp_response.split("#")[0], temp_response.split("#")[1]
    #
    #     return character_said, character_translated

if __name__ == '__main__':
    openai_chat_api = OpenaiChatApi(character_prompt=character_config.CHARACTER_PROMPT,
                                    target_model="gpt-3.5-turbo-16k",
                                    conversation_language="japanese",
                                    conversation_history="")

    while True:
        received_message = openai_chat_api.send_my_message(input())
        print(received_message)

    # "gpt-4-1106-preview",
    # "gpt-4-vision-preview",
    # "gpt-4",
    # "gpt-4-0314",
    # "gpt-4-0613",
    # "gpt-4-32k",
    # "gpt-4-32k-0314",
    # "gpt-4-32k-0613",
    # "gpt-3.5-turbo",
    # "gpt-3.5-turbo-16k",
    # "gpt-3.5-turbo-0301",
    # "gpt-3.5-turbo-0613",
    # "gpt-3.5-turbo-1106",
    # "gpt-3.5-turbo-16k-0613",