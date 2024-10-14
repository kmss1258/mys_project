import os
import api_config
import character_config
import program_config
import time
import sys
import threading
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import sys

from stt_module import SpeechToTextConverter
from tts_module import TextToSpeechConverter
from gpt_module import OpenaiChatApi
from translation_module import DeepLTranslator

class BackendWorker(QThread):
    # Define a signal that you can emit with the updated dialogue text
    updateDialogue = pyqtSignal(str)

    def __init__(self, tts_api_class, openai_chat_api_class, translator_api_class : DeepLTranslator, character_first_saying):
        super().__init__()
        self.tts_api_class = tts_api_class
        self.openai_chat_api_class = openai_chat_api_class
        self.translator_api_class = translator_api_class
        self.character_first_saying = character_first_saying

        self.is_running = True

    def set_user_message_variable_from_parent(self, parent_message_variable : list):
        self.user_input_text_list = parent_message_variable

    def get_user_message_from_parent(self):
        return self.user_input_text_list[0]

    def set_user_message_from_parent(self, message=""):
        self.user_input_text_list[0] = message

    def run(self):

        self.updateDialogue.emit(self.character_first_saying.replace("\n\n", "\n"))

        while self.is_running:
            user_message = self.get_user_message_from_parent()
            if user_message == "":
                time.sleep(0.1)
                continue

            # Message Received From Main Class
            character_emotion, character_said, character_whole_response = self.openai_chat_api_class.send_my_message(user_message)

            translate_thread = threading.Thread(target=self.translator_api_class.translate, args=(character_said, ))

            translate_thread.start()
            translate_thread.join()

            sound_thread = threading.Thread(target=self.tts_api_class.play_character_sound, args=(tts_api.send_request(self.translator_api_class.last_translation_result),))
            sound_thread.start()

            self.updateDialogue.emit(character_whole_response)

            self.set_user_message_from_parent(message="")
            time.sleep(0.25)

    def stop(self):
        self.is_running = False  # Signal the thread to stop


# Application class
class VisualNovelApp(QtWidgets.QMainWindow):
    def __init__(self, backend_worker : BackendWorker, stt_api_class : SpeechToTextConverter, font_path, font_size,
                 character_nick_name, character_sub_nick_name):
        super().__init__()

        self.backend_worker = backend_worker
        self.font_size = font_size
        self.font = QtGui.QFont()
        self.loadFont(font_path)
        self.character_nick_name = character_nick_name
        self.character_sub_nick_name = character_sub_nick_name

        self.stt_api_class = stt_api_class

        # class variable share with BackendWorker
        self.user_input_text_list = [""]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.periodicFunction)
        self.timer.start(250) # every 250 milliseconds term execute.

        self.backend_worker.set_user_message_variable_from_parent(self.user_input_text_list)

        self.initUI()
        self.show()


    def periodicFunction(self):
        received_stt_text = self.stt_api_class.get_user_stt_text() # Don't have to set "" to stt_api
        if received_stt_text != "":
            self.user_input_text_list[0] = received_stt_text

    def loadFont(self, font_path):
        # Load the custom font
        QtGui.QFontDatabase.addApplicationFont(font_path)
        self.font.setFamily("경기천년제목 medium")  # Replace with the actual font family name
        self.font.setPointSize(self.font_size)

    def initUI(self):
        # Set the size and position of the window
        self.setGeometry(100, 100, 800, 600 - 105)
        self.setWindowTitle('mys')

        # Set up the background
        self.backgroundLabel = QtWidgets.QLabel(self)
        self.backgroundPixmap = QtGui.QPixmap("asset/koharu/background_images/background.png")
        self.backgroundLabel.setPixmap(self.backgroundPixmap.scaled(800, 455)) # QtCore.Qt.KeepAspectRatio))
        self.backgroundLabel.resize(800, 455)

        # Set up the character image
        window_height = self.geometry().height()
        character_height = int(window_height * 4 / 5)

        self.characterLabel = QtWidgets.QLabel(self)
        self.characterPixmap = QtGui.QPixmap(
            "asset/koharu/character_images/koharu.png").scaledToHeight(character_height,
                                                                       QtCore.Qt.SmoothTransformation)


        self.characterLabel.setPixmap(self.characterPixmap)
        self.characterLabel.setStyleSheet("background:transparent;")
        self.characterLabel.resize(self.characterPixmap.size())

        window_width = self.geometry().width()  # 창의 너비를 가져옵니다.
        character_width = self.characterPixmap.width()  # 조절된 이미지의 너비
        x_position = (window_width - character_width) // 2

        # Calculate the y position to place the character image at the bottom
        y_position = window_height - character_height - 40

        self.characterLabel.move(x_position, y_position)
        # self.characterLabel.move(150, 0)  # Center the character on the screen

        # Set up the dialogue box for character's message
        self.dialogueLabel = QtWidgets.QLabel(self)
        gradient_style = """
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                stop:0 rgba(27, 35, 44, 0), stop:0.2 rgba(27, 35, 44, 200));
                padding: 10px; /* Top and Bottom Padding */
                padding-left: 40px; /* Left Padding */
                padding-right: 40px; /* Right Padding */
                color: white;
                border: none;
                word-wrap: break-word;
                """
        self.dialogueLabel.setStyleSheet(gradient_style)
        self.dialogueLabel.setGeometry(QtCore.QRect(0, 380 - 105, 800, 180))
        self.dialogueLabel.setFont(self.font)
        self.dialogueLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.dialogueLabel.setWordWrap(True)

        # Set up the user input line
        self.userInput = QtWidgets.QLineEdit(self)
        self.userInput.setGeometry(QtCore.QRect(0, 560 - 105, 750, 40))
        self.userInput.setStyleSheet("""QLineEdit {
                                            background-color: rgba(0, 0, 0, 0.9);
                                            padding-left: 20px; /* Left Padding */
                                            color: white;
                                            border: none;
                                     }""")
        self.userInput.returnPressed.connect(self.onEnter)
        self.userInput.setFont(self.font)

        # Set up the send button
        self.sendButton = QtWidgets.QPushButton(">", self)  # Paper airplane emoji as label
        self.sendButton.setFont(self.font)
        self.sendButton.setGeometry(QtCore.QRect(750, 560 - 105, 50, 40))  # Position next to the input line
        self.sendButton.clicked.connect(self.onEnter)  # Connect the button to the same slot as returnPressed
        self.sendButton.setStyleSheet("background-color: rgba(0, 0, 0, 0.9); color: white;")

        # self.characterNameLabel = QtWidgets.QLabel(f"{self.character_nick_name}", self)
        # self.font.setPointSize(22)
        self.characterNameLabel = QtWidgets.QLabel(self)
        self.characterNameLabel.setFont(self.font)  # Assuming you have a font set up
        self.characterNameLabel.setGeometry(QtCore.QRect(50, 295, 700, 30))  # Adjust the position and size as needed
        self.setCharacterName(self.character_nick_name, self.character_sub_nick_name)

        # self.characterNameLabel.setStyleSheet("background-color: rgba(0, 0, 0, 0.0); color: white;")

        # Set up the line under the character name label
        self.line = QtWidgets.QFrame(self)
        self.line.setGeometry(QtCore.QRect(50, 330, 700, 3))  # Adjust the position and size to align with the label
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setStyleSheet("color: white;")

        ###################################### GUI END ########################################







        # Remove window frame
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.dialogue_timer = QTimer(self)
        self.dialogue_timer.timeout.connect(self.updateText)
        self.current_dialogue = ""
        self.dialogue_index = 0

        self.thread = QThread()
        self.backend_worker.moveToThread(self.thread)  # Move the worker to the thread
        self.backend_worker.updateDialogue.connect(self.updateDialogueLabel)  # Connect signal to slot
        self.thread.started.connect(self.backend_worker.run)  # Start the worker when the thread starts
        self.thread.start()  # Start the thread

    def setCharacterName(self, character_nickname, character_sub_nickname):
        # Use HTML to format the text with different styles
        formatted_text = f"<span style='color: white; font-size: 22pt;'>{character_nickname}</span>" \
                         f"<span style='color: rgb(141, 200, 232); font-size: 16pt;'> {character_sub_nickname}</span>"
        self.characterNameLabel.setText(formatted_text)

    def updateDialogueLabel(self, text):
        # Reset the text updating mechanism
        self.current_dialogue = text
        self.dialogue_index = 0
        self.dialogueLabel.setText("\n\n")  # Clear the label and add padding if needed
        self.dialogue_timer.start(50)  # Adjust the typing speed as needed

    def updateText(self):
        if self.dialogue_index < len(self.current_dialogue):
            # Append next character
            self.dialogueLabel.setText(self.dialogueLabel.text() + self.current_dialogue[self.dialogue_index])
            self.dialogue_index += 1
        else:
            # Stop the timer if the end of the dialogue is reached
            self.dialogue_timer.stop()

    def onEnter(self):
        self.user_input_text_list[0] = self.userInput.text()
        self.userInput.clear()  # Clear the input field

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QtCore.QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def closeEvent(self, event):
        # This method is called when the window is closed.
        self.backend_worker.stop()  # Signal the worker thread to stop
        self.backend_worker.wait()  # Wait for the worker thread to finish
        event.accept()  # Accept the close event
        os._exit()


if __name__ == '__main__':
    # Run the application
    # pyinstaller --onefile --noconsole --icon=asset/icon_64.ico main.py
    # pyinstaller --onefile --add-data "asset;asset" --add-data "asset/MainFont.ttf;asset" --add-data "asset/background_images;asset/background_images" --add-data "asset/background_images/background.png;asset/background_images" --add-data "asset/character_images;asset/character_images" --add-data "asset/character_images/louise.png;asset/character_images" --noconsole --icon=asset/icon_64.ico main.py

    is_debug = True

    project_folder_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "MYS_PROJECT", character_config.CHARACTER_NAME)
    stt_api = SpeechToTextConverter(client_id=api_config.RETURN_ZERO_CLIENT_ID,
                                    client_secret=api_config.RETURN_ZERO_API_KEY,
                                    home_directory=project_folder_dir,
                                    is_debug=is_debug)

    # TTSAPI 클래스의 인스턴스 생성
    character_config_list = api_config.CHARACTER_API_CONFIG_DICT[character_config.CHARACTER_NAME]
    tts_api = TextToSpeechConverter(api_url=character_config_list[1], speech_language="japanese",
                                    character_config=character_config_list[0], home_directory=project_folder_dir, is_debug=is_debug)

    openai_chat_api = OpenaiChatApi(character_prompt=character_config.CHARACTER_PROMPT,
                                    target_model="gpt-3.5-turbo-16k",
                                    conversation_language=character_config.CONVERSATION_LANGUAGE,
                                    translation_language=character_config.TRANSLATION_LANGUAGE,
                                    conversation_history="",
                                    character_first_saying=character_config.INITIAL_MESSAGE,
                                    sub_prompt=character_config.SUB_PROMPT,
                                    is_debug=is_debug)

    translator_api = DeepLTranslator(auth_key=api_config.DEEPL_API_KEY,
                                     target_language=character_config.CONVERSATION_LANGUAGE,
                                     is_debug=is_debug)

    app = QtWidgets.QApplication(sys.argv)
    backend_worker = BackendWorker(tts_api_class=tts_api, openai_chat_api_class=openai_chat_api,
                                   translator_api_class=translator_api, character_first_saying=character_config.INITIAL_MESSAGE)
    font_path = "asset/MainFont.ttf"
    font_size = 18
    ex = VisualNovelApp(backend_worker, stt_api, font_path, font_size,
                        character_nick_name=character_config.CHARACTER_NICK_NAME,
                        character_sub_nick_name=character_config.CHARACTER_SUB_NICK_NAME)
    sys.exit(app.exec_())

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