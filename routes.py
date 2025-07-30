from flask import Blueprint, render_template, request, jsonify
from controllers.userController import addUser, getUser, predictLetters, predictWords
import speech_recognition as sr
import io
from pydub import AudioSegment
import os
import json
import requests
import asyncio
import websockets
import threading
from translate import translate
r = sr.Recognizer()

main = Blueprint('main', __name__)

# WebSocket Server Variables
clients = set()
ws_server = None
loop = None

# WebSocket Functions
async def websocket_handler(websocket):  # ✅ بدون path

    print("✅ Unity Client connected!")
    clients.add(websocket)
    try:
        async for message in websocket:
            print(f"📥 Received from Unity: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Unity Client disconnected!")
    finally:
        clients.remove(websocket)

async def send_to_unity(animation_name):
    if clients:
        for client in clients:
            await client.send(animation_name)
        print(f"✅ Sent animation to Unity: {animation_name}")
    else:
        print("⚠️ No active Unity connections!")

def start_websocket_server():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_server():
        async with websockets.serve(websocket_handler, "0.0.0.0", 5001):
            print("🚀 WebSocket Server running on ws://0.0.0.0:5001 (for Unity)")
            await asyncio.Future()  # علشان السيرفر يفضل شغال

    loop.run_until_complete(run_server())


def run_websocket_server():
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()

# Audio Processing Functions
def get_best_animation(user_input):
    animations_folder = 'animations'

    def read_animations_json():
        if os.path.exists('animations.json'):
            with open('animations.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        return {}

    def get_animation_files():
        new_animations = {}
        if os.path.exists(animations_folder):
            for filename in os.listdir(animations_folder):
                if filename.endswith(".anim"):
                    animation_name = os.path.splitext(filename)[0]
                    new_animations[animation_name] = None
        return new_animations

    new_animations = get_animation_files()
    if new_animations:
        with open('animations.json', 'w', encoding='utf-8') as file:
            json.dump(new_animations, file, ensure_ascii=False, indent=4)

    available_animations = ', '.join(read_animations_json().keys())

    prompt = f"""
    This is a program that converts spoken phrases into sign language animations using a Unity-based avatar.
    I will send you the user's input text, and I want you to choose which animation clip name should be played from the available ones.
    The available animation clip names are: {available_animations}

    Please consider that the input might contain extra spaces, typos, or slight differences in spelling. Please match the closest animation clip name from the available list, even if the spelling or spacing isn't exact. 
    If the input is close to an animation name but not an exact match, choose the closest name from the list. 
    If none of the animations match closely enough, return only the word 'none'.

    This is the user's input: {user_input}
    """

    GEMINI_API_KEY = "AIzaSyAjiN6AKNgdTqyb26Wvb4RPO31mX5pO-7M"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"Selected Animation: {result.strip()}")
        return result.strip()
    else:
        print(f"Error in animation selection: {response.text}")
        return "none"

@main.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        return "لم يتم إرسال ملف صوتي", 400

    file = request.files['audio']
    if file.filename == '':
        return "الملف المرسل غير صالح", 400

    try:
        # تحويل الملف من webm إلى wav (أو حسب الصيغة)
        audio = AudioSegment.from_file(io.BytesIO(file.read()), format="webm")
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)

        # التعرف على الكلام
        with sr.AudioFile(wav_io) as source:
            audio_data = r.record(source)

        try:
            recognized_text = r.recognize_google(audio_data, language='ar-AR')
        except sr.UnknownValueError:
            print("❌ لم يتم التعرف على الصوت")
            return "لم يتم التعرف على الصوت، حاول مرة أخرى", 400
        except sr.RequestError as e:
            print(f"❌ مشكلة في الاتصال بخدمة Google: {e}")
            return "مشكلة في خدمة التعرف على الصوت، حاول لاحقًا", 500

        # إرسال النتيجة إلى Unity
        animation_result = get_best_animation(recognized_text)
        asyncio.run_coroutine_threadsafe(send_to_unity(animation_result), loop)
        

        return recognized_text

    except Exception as e:
        print(f"❌ خطأ أثناء معالجة الملف: {str(e)}")
        return "حدث خطأ أثناء معالجة الصوت، حاول مرة أخرى", 500


# Original Routes
@main.route('/login', methods=['GET','POST'])
def login():
    result = getUser()
    if result == True:
        return render_template('About us.html')
    else:
        return render_template('login.html')

@main.route('/', methods=['GET','POST'])
def register():
    result = addUser()
    if result == True:
        return render_template('login.html')
    else:
        return render_template('registration.html')

@main.route('/predict', methods=['GET', 'POST'])
def letterPredict():
    prediction = predictLetters()
    return prediction

@main.route('/upload_video', methods=['GET','POST'])
def wordsPredict():
    prediction = predictWords()
    return prediction

@main.route('/home', methods=['GET'])
def home():
    return render_template('index.html')

@main.route('/about', methods=['GET'])
def about():
    return render_template('About us.html')

@main.route('/game')
def sameh():
    return render_template('game.html')

@main.route('/sameh2')
def sameh2():
    return render_template('words.html')

@main.route('/translate', methods=['POST'])
def translate_endpoint():
    # Accept JSON or form data
    data = request.get_json() or request.form
    text = data.get('text')
    lang = data.get('lang')
    
    # Check for missing parameters
    if not text or not lang:
        return jsonify({"error": "Missing 'text' or 'lang' parameter"}), 400

    try:
        # Translate the text
        translated_text = translate(text, lang)
        return jsonify({"translation": translated_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



