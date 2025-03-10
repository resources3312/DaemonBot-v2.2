#! /usr/bin/python
from telebot import TeleBot, util
from platform import platform, processor
from time import sleep, time
import sys
import os
import socket
from psutil import sensors_battery, boot_time, process_iter
from subprocess import getoutput, Popen
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from keyboard import press_and_release
from dotenv import load_dotenv
from datetime import datetime
import pyttsx3
from sqlite3 import connect
import requests

driver = None

load_dotenv()

bot = TeleBot(os.getenv("TOKEN"))

MODE: str = "normal"

def get_info_ipv4() -> str:
    """
    Returning local or global ipv4
    
    no argument - Local ipv4
    
    -w, --wan - Global ipv4 
    
    Not connection - 127.0.0.1
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except socket.error: return "127.0.0.1"


def definedistr() -> str:
    """
    Returning your linux distribtion from os-release
    file
    
    """
    try:
        with open('/etc/os-release', 'r', encoding="utf-8") as f:
            return f.read().split()[9].split('=')[1].lower()
    except EOFError: return 

def conf_write_option(file: str, param: str, option: str) -> None:
    """
    Changing option in config file
    
    """
    try:
        with open(file, "r", encoding="utf-8") as f:
            raw = f.read().split()
            index = raw.index(param)
            with open(file, "r", encoding="utf-8") as f:
                text = f.read()
                data = text.replace(raw[index], option)
                with open(file, "w", encoding="utf-8") as f:
                    f.write(data)
    except (EOFError, IndexError): pass

def conf_write_value(file: str, param: str, option: str) -> None:
    """
    Changing value of option in config file
    
    """
    try:
        with open(file, "r", encoding="utf-8") as f:
            raw = f.read().split()
            index = raw.index(param) + 1
            with open(file, "r", encoding="utf-8") as f:
                text = f.read()
                data = text.replace(raw[index], option)
                with open(file, "w", encoding="utf-8") as f:
                    f.write(data)
    except (EOFError, IndexError): pass

def user_validate(user_id: int) -> int:
    try:
        with open("users.txt", "r") as f:
            for user in f.read().splitlines():
                if str(user_id) in user: return int(user.split("|")[1]) 
            return -1 
    except: return -2

def init_ssh() -> str:
    """
    Installi if not installed, and running SSH-server

    """
    if "nt" in os.name: return get_info_ipv4()
        # In development stage
    else:
        if "not found" in getoutput("which sshd"):
            match definedistr():
                case "debian":
                    os.system('apt update -y')
                    os.system('apt install openssh-server -y')
                case "ubuntu":
                    os.system('apt update -y')
                    os.system('apt install openssh-server -y')
                case "centos":
                    pass
                case "fedora":
                    os.system("dnf update")
                    os.system('dnf install openssh-server -y')
                case "arch":
                    os.system('pacman -Sy')
                    os.system('pacman -S openssh')
                case "gentoo":
                    os.system('emerge --sync')
                    os.system('emerge openssh')
            conf_write_option("/etc/ssh/sshd_config", "#ListenAddress", "ListenAddress")
            conf_write_option("/etc/ssh/sshd_config", "#Port", "Port")
        conf_write_value("/etc/ssh/sshd_config", "ListenAddress", get_info_ipv4())
        os.system("systemctl restart ssh")
        return get_info_ipv4()

def get_device_data(location: str, device_data: str) -> list:
    with connect("testdb.db") as db:
        query = db.cursor().execute(f'SELECT * FROM devices WHERE location="{location}" AND (name="{device_data}" OR type="{device_data}")')
        return [{"ipv4": i[1], "location": i[2], "name": i[3],"type": i[4], "username": i[5], "passwd": i[6], "command": json.loads(i[7]), "protocol": i[8]} for i in query.fetchall()] 

def init_database() -> None:
    with connect("testdb.db") as db:
        db.cursor().execute("""CREATE TABLE IF NOT EXISTS devices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ipv4 TEXT NOT NULL,
            location TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            username TEXT,
            passwd TEXT,
            command TEXT NOT NULL,
            protocol TEXT NOT NULL
            )
""")
        db.commit()

@bot.message_handler(func=lambda message: "https://" in message.text and "youtu" in message.text and user_validate(message.chat.id) == 0, content_types=["text"])
def open_url(message):
    try: 
        global driver
        driver = webdriver.Firefox()
        driver.get(message.text)
        driver.maximize_window()
        driver.find_element(By.XPATH,'//*[@id="movie_player"]').click()
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, f"<b>{driver.title}</b>\n\n<b>Предупреждение</b>\nСоблюдайте правило <b>одно меню - одно видео</b>, и не забывайте закрывать видео с помощью кнопки закрыть", reply_markup=util.quick_markup(
            {"Закрыть": {"callback_data": "player_kill"} ,
             "Запустить/Приостановить": {"callback_data": "player_switch"}, 
             "Полноэкранный режим": {"callback_data": "player_fullscreen"},
             "Увеличить громкость": {"callback_data": "player_volume_up"}, 
             "Уменьшить громкость": {"callback_data": "player_volume_down"}, 
             "Включить/Отключить звук": {"callback_data": "player_volume_mute"},
             "Воспроизвести заново": {"callback_data": "player_replay"},
             "Перемотка назад": {"callback_data": "player_back"},
             "Перемотка вперед": {"callback_data": "player_front"}
             }, row_width=1), parse_mode="html")
    except: driver.quit(), bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, f"Не удалось открыть <code>{message.text}</code>\nПроверьте ссылку и попробуйте еще раз", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}}), parse_mode="html")

@bot.message_handler(func=lambda message: MODE == "file" and user_validate(message.from_user.id) == 0, content_types=["text"])
def send_document(message):
    try:
        with open(message.text, "rb") as file:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_document(message.chat.id, file)
    except: bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Файл не найден на диске, попробуйте еще раз")

@bot.message_handler(func=lambda message: MODE == "file" and user_validate(message.from_user.id) == 0, content_types=["document"])
def get_document(message):
    try:
        with open(str(message.document.file_name), "wb") as f:
            f.write(ot.download_file(bot.get_file(message.document.file_id).file_path))
            bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Ваш файл был сохранен на диске", reply_markup=util.quick_markup({"В главное иеню": {"callback_data": "main"}})) 
    except: bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Ваш файл не был сохранен на диске, проверьте файл и попробуйте еще раз", reply_markup=util.quick_markup({"В главное иеню": {"callback_data": "main"}})) 


@bot.message_handler(func=lambda message: MODE == "file" and user_validate(message.from_user.id) == 0, content_types=["photo"])
def get_photo(message):
    try:
        with open(str(message.photo.file_name), "wb") as f:
            f.write(bot.download_file(bot.get_file(message.photo[-1].file_id).file_path))
            bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Ваш файл был сохранен на диске", reply_markup=util.quick_markup({"В главное иеню": {"callback_data": "main"}})) 


    except: bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Ваш файл не был сохранен на диске, проверьте файл и попробуйте еще раз", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}})) 


@bot.message_handler(func=lambda message: MODE == "file" and user_validate(message.from_user.id) == 0, content_types=["video"])
def get_video(message):
    try:
        with open(message.video.file_name, "wb") as f:
            f.write(bot.download_file(bot.get_file(message.video.file_id).file_path))
            bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Ваш файл был сохранен на диске", reply_markup=util.quick_markup({"В главное иеню": {"callback_data": "main"}}))
    
    except: bot.delete_message(message.chat.id, message.message_id), bot.send_message(message.chat.id, "Ваш файл не был сохранен на диске, проверьте файл и попробуйте еще раз", reply_markup=util.quick_markup({"В главное иеню": {"callback_data": "main"}})) 


@bot.message_handler(func=lambda message: MODE == "process_run" and "http" not in message.text and user_validate(message.from_user.id) == 0)
def run_process(message):
    try: bot.delete_message(message.chat.id, message.message_id), Popen(message.text) 
    except: bot.send_message(message.chat.id, "Не удалось запустить процесс, попробуйте еще раз", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}}))

@bot.message_handler(func=lambda message: MODE == "process_kill" and "http" not in message.text and user_validate(message.from_user.id) == 0)
def stop_process(message):
    try: bot.delete_message(message.chat.id, message.message_id), [ps.kill() for ps in process_iter(["name"]) if ps.info["name"].lower() == message.text] 
    except: bot.send_message(message.chat.id, "Не удалось остановить процесс, попробуйте еще раз", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}}))

@bot.message_handler(func=lambda message: "http" not in message.text and MODE == "voice" and user_validate(message.from_user.id) != -1)
def speaker_handler(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
        engine = pyttsx3.init()
        engine.say(message.text)
        engine.runAndWait()
    except: bot.send_message(message.chat.id, "Не удалось озвучить реплику")

@bot.message_handler(func=lambda message: MODE == "smart_home" and user_validate(message.from_user.id) == 0)
def smart_home_handler(message):
    try:
        for i in get_device_data(message.text.split(" ")[1], message.text.split(" ")[2]):
            match i["protocol"]:
                case "http":
                    try: requests.post(i["ipv4"], json=i["command"])
                    except: bot.send_message(message.chat.id, f"Не удалось связаться с устройством {i['name']}")
    except: bot.send_message(message.chat.id, "Не удалось выполнить команду, попробуйте ещё раз")

@bot.message_handler(commands=["start"])
def get_start(message):
    match user_validate(message.from_user.id):
        case -2: bot.send_message(message.chat.id, "<b>Ошибка сервера</b>\nНарушение целостности списка, свяжитесь с администратором", parse_mode="html")
        case 0:
            bot.send_message(message.chat.id, f"<b>Панель управления</b>\n\n<b>Имя устройства</b> - <code>{socket.gethostname()}</code>\n\n<b>Питание</b> - <code>{sensors_battery().percent if sensors_battery() else 'Подключено'}</code>\n\n<b>OC</b> - <code>{platform()}</code>\n\n<b>Процессор</b> - <code>{processor()}</code>\n\n<b>Локальный адрес</b> - <code>{get_info_ipv4()}</code>\n\n<b>Uptime</b> - <code>{str(datetime.fromtimestamp(boot_time()))[:-7]}</code>\n", reply_markup=util.quick_markup(
        {"Отключить машину": {"callback_data": "shutdown"},
         "Поднять ssh": {"callback_data": "ssh_up"}, 
        "Увеличить громкость": {"callback_data": "system_volume_up"},
         "Уменьшить громкость": {"callback_data": "system_volume_down"},
         "Включить/Отключить звук": {"callback_data": "system_volume_mute"},
         "Запустить процесс": {"callback_data": "process_run"},
         "Остановить процесс": {"callback_data": "process_kill"},
         "Отправка/Загрузка файлов": {"callback_data": "file_switch"},
         "Голосовой ввод": {"callback_data": "voice_switch"},
         "SmartHome": {"callback_data": "smart_home"}
         },row_width=1), parse_mode="html") 
        
        case 1:
            bot.send_message(message.chat.id, f"<b>Панель управления</b>\n\n<b>Имя устройства</b> - <code>{socket.gethostname()}</code>\n\n<b>Питание</b> - <code>{sensors_battery().percent if sensors_battery() else 'Подключено'}</code>\n\n<b>OC</b> - <code>{platform()}</code>\n\n<b>Процессор</b> - <code>{processor()}</code>\n\n<b>Локальный адрес</b> - <code>{get_info_ipv4()}</code>\n\n<b>Uptime</b> - <code>{str(datetime.fromtimestamp(boot_time()))[:-7]}</code>\n", reply_markup=util.quick_markup(
        {"Отключить машину": {"callback_data": "shutdown"},
         "Голосовой ввод": {"callback_data": "voice_switch"},
         }, row_width=1), parse_mode="html") 
        case 2: bot.send_message(message.chat.id, "<b>Разговорный режим</b>\nПока что вы можете лишь подать голос", reply_markup=util.quick_markup({"Голосовой ввод": {"callback_data": "voice_switch"}}), parse_mode="html")

@bot.callback_query_handler(func=lambda call: True)
def start_handler(call):
    global MODE
    match call.data:
        case "main": bot.send_message(call.message.chat.id, f"<b>Панель управления</b>\n\n<b>Имя устройства</b> - <code>{socket.gethostname()}</code>\n\n<b>Питание</b> - <code>{sensors_battery().percent if sensors_battery() else 'Подключено'}</code>\n\n<b>OC</b> - <code>{platform()}</code>\n\n<b>Процессор</b> - <code>{processor()}</code>\n\n<b>Локальный адрес</b> - <code>{get_info_ipv4()}</code>\n\n<b>Uptime</b> - <code>{str(datetime.fromtimestamp(boot_time()))[:-7]}</code>\n", reply_markup=util.quick_markup(
        {"Отключить машину": {"callback_data": "shutdown"},
         "Поднять ssh": {"callback_data": "ssh_up"}, 
        "Увеличить громкость": {"callback_data": "system_volume_up"},
         "Уменьшить громкость": {"callback_data": "system_volume_down"},
         "Включить/Отключить звук": {"callback_data": "system_volume_mute"},
         "Запустить процесс": {"callback_data": "process_run"},
         "Остановить процесс": {"callback_data": "process_kill"},
         "Отправка/Загрузка файлов": {"callback_data": "file_switch"},
         "Голосовой ввод": {"callback_data": "voice_switch"},
         "SmartHome": {"callback_data": "smart_home"}
         },row_width=1), parse_mode="html")   
        case "shutdown":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "Машина была отключена, чтобы вернуться в главное меню нажмите кнопку ниже", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}})), os.system(f"shutdown {'-h now' if 'nt' not in os.name else '/s -t 0'}")
        case "ssh_up": bot.delete_message(call.message.chat.id, call.message.message_id), bot.send_message(call.message.chat.id, f"<b>SSH сервер был запущен</b>\nЛокальный адрес - <code>{init_ssh()}</code>", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}}), parse_mode="html")
        case "process_run": MODE = "process_run" if MODE != "process_run" else "normal"
        case "process_kill": MODE = "process_kill" if MODE != "process_kill" else "normal"
        case "system_volume_up": press_and_release("volume up")
        case "system_volume_down": press_and_release("volume down")
        case "system_volume_mute": press_and_release("volume mute")
        case "player_kill": driver.quit(), bot.delete_message(call.message.chat.id, call.message.message_id), bot.send_message(call.message.chat.id, "Плеер был закрыт, чтобы вернуться в главное меню нажмите кнопку ниже", reply_markup=util.quick_markup({"В главное меню": {"callback_data": "main"}}))  
        case "player_switch": driver.find_element(By.XPATH,'//*[@id="movie_player"]').click() 
        case "player_volume_mute": driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys("m")
        case "player_volume_up": [driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys(Keys.ARROW_UP) for i in range(0, 2)]
        case "player_volume_down": [driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys(Keys.ARROW_DOWN) for i in range(0, 2)]
        case "player_front": driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys(Keys.ARROW_RIGHT)
        case "player_back": driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys(Keys.ARROW_LEFT)
        case "player_fullscreen": driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys("f")
        case "player_replay": driver.find_element(By.XPATH,'//*[@id="movie_player"]').send_keys("0")
        case "voice_switch": MODE = "voice" if MODE != "voice" else "normal"
        case "file_switch": MODE = "file" if MODE != "file" else "normal"
        case "smart_home": MODE = "smart_home" if MODE != "smart_home" else "normal"

def main() -> None:
    bot.infinity_polling()

if __name__ == '__main__': main() 
