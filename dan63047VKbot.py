"""Here you can found Bot class and Database worker class"""
import vk_api
import datetime
import time
import requests
import logging
import pyowm
import random
import json
import re
import threading
import pymysql
import wikipediaapi as wiki
import config
from pymysql.cursors import DictCursor
from pyowm.utils.config import get_default_config
from collections import deque
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
try:
    log_path = f'logs/bot_log{str(datetime.datetime.now())}.log'
    handler = logging.FileHandler(log_path, 'w', 'utf-8')
except:
    log_path = 'bot.log'
    handler = logging.FileHandler(log_path, 'w', 'utf-8')
handler.setFormatter(logging.Formatter('%(message)s'))
root_logger.addHandler(handler)
debug_array = {'vk_warnings': 0, 'db_warnings': 0, 'bot_warnings': 0,
               'logger_warnings': 0, 'start_time': 0, 'messages_get': 0, 'messages_answered': 0}


def log(warning, text):
    if warning:
        msg = "[" + str(datetime.datetime.now()) + "] [WARNING] " + text
        logging.warning(msg)
        print(msg)
        debug_array['logger_warnings'] += 1
    else:
        msg = "[" + str(datetime.datetime.now()) + "] " + text
        logging.info(msg)
        print(msg)

bot = {}
errors_array = {"access": "Отказано в доступе",
                "miss_argument": "Отсуствует аргумент", "command_off": "Команда отключена"}

try:
    vk = vk_api.VkApi(token=config.vk_group_token)
    longpoll = VkBotLongPoll(vk, config.group_id)
except Exception as e:
    log(True, "Can't connect to longpull: "+str(e))
    exit(log(False, "[SHUTDOWN]"))

try:
    if(config.vk_service_token != None and config.album_for_command):
        random_image_command = True
        vk_mda = vk_api.VkApi(token=config.vk_service_token)
        vk_mda.method('photos.get', {'owner_id': "-"+str(config.group_id),
                                     'album_id': config.album_for_command, 'count': 1000})
    if(config.album_for_command == None):
        log(False, "Album id for !image is not setted, command will be turned off")
    if(config.vk_service_token == None):
        random_image_command = False
        log(False, "Service token is 'None', !image command will be turned off")
except vk_api.ApiError:
    random_image_command = False
    log(True, "Invalid service token, !image command will be turned off")
except AttributeError:
    random_image_command = False
    log(True, "Service token or album id not found, !image command will be turned off")

try:
    if(config.openweathermap_api_key != None):
        owm_dict = get_default_config()
        owm_dict['language'] = 'ru'
        owm = pyowm.OWM(config.openweathermap_api_key, owm_dict)
        mgr = owm.weather_manager()
        mgr.weather_at_place("Минск")
        weather_command = True
    else:
        log(False, "OpenWeatherMap API key is 'None', !weather command will be turned off")
        weather_command = False
except AttributeError:
    weather_command = False
    log(True, "OpenWeatherMap API key not found, !image command will be turned off")
except Exception:
    weather_command = False
    log(True, "Invalid OpenWeatherMap API key, !weather command will be turned off")

class Database_worker():

    def __init__(self):
        if(config.use_database):
            log(False, "Trying to connect to database")
            try:
                self._CON = pymysql.connect(
                    host=config.mysql_host,
                    user=config.mysql_user,
                    password=config.mysql_pass,
                    db=config.mysql_db,
                    charset='utf8mb4',
                    cursorclass=DictCursor
                )
                cur = self._CON.cursor()
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True, f"Unable to connect to database: {str(e)}")
            try:
                cur.execute("SELECT * FROM bot_users")
            except:
                cur.execute("CREATE TABLE bot_users ( id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, chat_id INT UNSIGNED, awaiting VARCHAR(128), access TINYINT, midnight BOOL, new_post BOOL, admin_mode BOOL, game_wins INT UNSIGNED, game_defeats INT UNSIGNED, game_draws INT UNSIGNED)")
            cur.close()
            log(False, f"Database connection established")
        else:
            log(False, "Bot will use JSON file as database")
            try:
                with open("data.json", "r") as data:
                    self._DATA_DIST = json.load(data)
                    data.close()
            except Exception:
                log(True, "data.json is not exist, it will be created soon")
                self._DATA_DIST = {"users": {}}

    def set_new_user(self, peer_id, midnight=False, awaiting=None, access=1, new_post=False, admin_mode=False, game_wins=0, game_defeats=0, game_draws=0):
        if(config.use_database):
            try:
                cur = self._CON.cursor()
                cur.execute("INSERT INTO bot_users (chat_id, awaiting, access, midnight, new_post, admin_mode, game_wins, game_defeats, game_draws) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (peer_id, awaiting, access, midnight, new_post, admin_mode, game_wins, game_defeats, game_draws))
                self._CON.commit()
                cur.close()
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True, f"Unable to add new user in database: {str(e)}")
        else:
            self._DATA_DIST['users'][peer_id] = {"awaiting": awaiting, "access": access, "midnight": midnight, "new_post": new_post,
                                                 "admin_mode": admin_mode, "game_wins": game_wins, "game_defeats": game_defeats, "game_draws": game_draws}
            open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def get_all_users(self):
        if(config.use_database):
            try:
                cur = self._CON.cursor()
                cur.execute("SELECT * FROM bot_users")
                result = cur.fetchall()
                cur.close()
                return result
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True, f"Unable to load user from database: {str(e)}")
        else:
            return self._DATA_DIST['users']

    def get_from_users(self, from_id):
        if(config.use_database):
            try:
                cur = self._CON.cursor()
                cur.execute(
                    "SELECT * FROM bot_users WHERE chat_id = %s", (from_id))
                result = cur.fetchall()
                cur.close()
                return result
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True, f"Unable to load user from database: {str(e)}")
        else:
            return self._DATA_DIST['users'][str(from_id)]

    def get_game_stat(self):
        if(config.use_database):
            try:
                cur = self._CON.cursor()
                cur.execute(
                    "SELECT chat_id, game_wins, game_draws, game_defeats FROM bot_users WHERE game_wins > 0 OR game_draws > 0 OR game_defeats > 0")
                result = cur.fetchall()
                cur.close()
                return result
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True, f"Unable to load stats from database: {str(e)}")
        else:
            return self._DATA_DIST['users']
            # Info: dist cannot return only the necessary keys

    def update_user(self, chat_id, thing, new_value):
        if(config.use_database):
            try:
                cur = self._CON.cursor()
                cur.execute(
                    f"UPDATE bot_users SET {thing} = %s WHERE bot_users.chat_id = %s;", (new_value, chat_id))
                self._CON.commit()
                cur.close()
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True,
                    f"Unable to update info about user in database: {str(e)}")
        else:
            self._DATA_DIST['users'][str(chat_id)][thing] = new_value
            open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def delete_user(self, chat_id):
        if(config.use_database):
            try:
                cur = self._CON.cursor()
                cur.execute(
                    "DELETE FROM bot_users, game_defeats WHERE chat_id = %s", (chat_id))
                self._CON.commit()
                cur.close()
                return True
            except Exception as e:
                debug_array['db_warnings'] += 1
                log(True, f"Unable to delete user from database: {str(e)}")
                return False
        else:
            self._DATA_DIST['users'].pop(str(chat_id))
            open("data.json", "w").write(json.dumps(self._DATA_DIST))


db = Database_worker()


def load_users():
    try:
        log(False, "Reading database")
        get_info = db.get_all_users()
        if(config.use_database):
            for i in get_info:
                bot[int(i['chat_id'])] = VkBot(int(i['chat_id']), bool(i['midnight']), i['awaiting'], int(
                    i['access']), bool(i['new_post']), bool(i['admin_mode']))
        else:
            for i in get_info:
                bot[int(i)] = VkBot(int(i), bool(get_info[i]['midnight']), get_info[i]['awaiting'], int(
                    get_info[i]['access']), bool(get_info[i]['new_post']), bool(get_info[i]['admin_mode']))
    except Exception as lol:
        debug_array['bot_warnings'] += 1
        log(True, f"Problem with creating objects: {str(lol)}")


def toFixed(numObj, digits=0):
    return f"{numObj:.{digits}f}"


class MyVkLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except Exception as e:
                err = "A problem with VK LongPull: " + str(e)
                log(True, err)
                debug_array['vk_warnings'] += 1
                time.sleep(15)
                continue


def create_new_bot_object(chat_id):
    bot[chat_id] = VkBot(chat_id)
    db.set_new_user(chat_id)


def get_weather(place):
    try:
        weather_request = mgr.weather_at_place(place)
    except Exception as i:
        err = "A problem with OpenWeather API: " + str(i)
        log(True, err)
        return "Такого города нет, либо данных о погоде нет"
    weather_status = weather_request.weather.detailed_status
    weather_temp = weather_request.weather.temperature('celsius')
    weather_humidity = weather_request.weather.humidity
    weather_wing = weather_request.weather.wind()
    return f"Погода в городе {place}<br> {str(round(weather_temp['temp']))}°C, {weather_status}<br>Влажность: {weather_humidity}%<br>Ветер: {weather_wing['speed']} м/с"


class VkBot:
    """Bot object, which can answer to user commands\n\n

    Keyword arguments:\n
    peer_id -- id of conversation with user for answering. Int\n
    midnight -- flag of midnight function, which send every midnigtht a message. Defalt: False. Bool\n
    awaiting -- strind, what show, which function awaiting input. Defalt: None. Str\n
    access -- flag, what set access level to bot functions. Defalt: True. Bool\n
    new_post -- flag of notificaton function about new post on group. Defalt: False. Bool\n
    admin_mode -- flag of moderating function, which moderate conversation. Defalt: False. Bool
    """
    
    def __init__(self, peer_id, midnight=False, awaiting=None, access=True, new_post=False, admin_mode=False):
        """Initialise the bot object\n\n

        Keyword arguments:\n
        peer_id -- id of conversation with user for answering. Int\n
        midnight -- flag of midnight function, which send every midnigtht a message. Defalt: False. Bool\n
        awaiting -- strind, what show, which function awaiting input. Defalt: None. Str\n
        access -- flag, what set access level to bot functions. Defalt: True. Bool\n
        new_post -- flag of notificaton function about new post on group. Defalt: False. Bool\n
        admin_mode -- flag of moderating function, which moderate conversation. Defalt: False. Bool
        """
        log(False, f"[BOT_{peer_id}] Created new bot-object")
        self._CHAT_ID = peer_id
        self._AWAITING_INPUT_MODE = awaiting
        self._ACCESS_TO_ALL = access
        self._SET_UP_REMINDER = {"task": None, "time": None}
        self._MIDNIGHT_EVENT = midnight
        self._NEW_POST = new_post
        self._ADMIN_MODE = admin_mode

        if int(self._CHAT_ID) == int(config.owner_id):
            self._OWNER = True
        else:
            self._OWNER = False

        self._COMMANDS = ["!image", "!my_id", "!h", "!user_id", "!group_id", "!help", "!weather", "!wiki", "!byn",
                          "!echo", "!game", "!debug", "!midnight", "!access", "!turnoff", "!ban", "!subscribe", "!random", "!admin_mode"]

    def __str__(self):
        return f"[BOT_{str(self._CHAT_ID)}] a: {str(self._ACCESS_TO_ALL)}, mn: {str(self._MIDNIGHT_EVENT)}, await: {str(self._AWAITING_INPUT_MODE)}, sub: {str(self._NEW_POST)}, adm: {str(self._ADMIN_MODE)}"

    def __del__(self):
        log(False, f"[BOT_{str(self._CHAT_ID)}] Bot-object has been deleted")

    def event(self, event, something=None):
        if event == "midnight" and self._MIDNIGHT_EVENT:
            current_time = datetime.datetime.fromtimestamp(time.time() + 10800)

            midnight_text = ["Миднайт!", "Полночь!", "Midnight!",
                             "миднигхт", "Середина ночи", "Смена даты!", "00:00"]
            if(random_image_command):
                self.send(
                    f"{random.choice(midnight_text)}<br>Наступило {current_time.strftime('%d.%m.%Y')}<br>Картинка дня:", self.random_image())
            else:
                self.send(
                    f"{random.choice(midnight_text)}<br>Наступило {current_time.strftime('%d.%m.%Y')}")
            log(False, f"[BOT_{self._CHAT_ID}] Notified about midnight")
        elif event == "post" and self._NEW_POST:
            post = f"wall{str(something['from_id'])}_{str(something['id'])}"
            self.send(f"Вышел новый пост", post)
            log(False, f"[BOT_{self._CHAT_ID}] Notified about new post")

    def get_message(self, event):
        message = event.message.text
        user_id = event.message.from_id
        if self._ADMIN_MODE:
            if message.find("@all") != -1 or message.find("@online") != -1 or message.find("@here") != -1 or message.find("@everyone") != -1 or message.find("@здесь") != -1 or message.find("@все") != -1:
                self.send(f"[@id{user_id}|Дебил]")
                try:
                    if int(user_id) != int(config.owner_id):
                        vk.method("messages.removeChatUser", {"chat_id": int(
                            self._CHAT_ID)-2000000000, "member_id": user_id})
                        log(False,
                            f"[BOT_{self._CHAT_ID}] user id{user_id} has been kicked")
                    else:
                        log(False, f"[BOT_{self._CHAT_ID}] can't kick owner")
                except Exception as e:
                    log(True,
                        f"[BOT_{self._CHAT_ID}] can't kick user id{user_id} - {str(e)}")
            with open('bad_words.txt', 'r', encoding="utf-8", newline='') as filter:
                flag = False
                forcheck = message.lower()
                for word in filter:
                    if flag:
                        if random.randint(0, 5) == 1:
                            self.send("За м*т извенись")
                        break
                    else:
                        if forcheck.find(word[:-1]) != -1:
                            flag = True
            if event.message.action:
                action = event.message.action
                if action['type'] == 'chat_invite_user' or action['type'] == 'chat_invite_user_by_link':
                    user_info = vk.method('users.get', {'user_ids': action["member_id"], 'fields': 'verified,last_seen,sex'})
                    self.send(f'Добро пожаловать в беседу, {user_info[0]["first_name"]} {user_info[0]["last_name"]}')
                elif action['type'] == 'chat_kick_user':
                    user_info = vk.method('users.get', {'user_ids': action["member_id"], 'fields': 'verified,last_seen,sex'})
                    self.send(f'{user_info[0]["first_name"]} {user_info[0]["last_name"]} покинул беседу')
        if self._AWAITING_INPUT_MODE:
            if message == "Назад":
                self.change_await()
                self.send("Отменено")
            else:
                if self._AWAITING_INPUT_MODE == "echo":
                    if message == "!echo off":
                        self.send("Эхо режим выключен")
                        self.change_await()
                        log(False, f"[BOT_{self._CHAT_ID}] Out from echo mode")
                    else:
                        self.send(message)
                        log(False,
                            f"[BOT_{self._CHAT_ID}] Answer in echo mode")
        else:
            if message.lower() == "бот дай денег":
                self.send("Иди нахуй")
            respond = {'attachment': None, 'text': None}
            message = message.split(' ', 1)
            if message[0] == self._COMMANDS[0]:
                if(random_image_command):
                    respond['attachment'] = self.random_image()
                else:
                    respond['text'] = errors_array["command_off"]

            elif message[0] == self._COMMANDS[1]:
                respond['text'] = "Ваш ид: " + str(user_id)

            elif message[0] == self._COMMANDS[2] or message[0] == self._COMMANDS[5]:
                with open('help.txt', 'r') as h:
                    help = h.read()
                    respond['text'] = help
                    h.close()

            elif message[0] == self._COMMANDS[3]:
                try:
                    respond['text'] = self.get_info_user(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == self._COMMANDS[4]:
                try:
                    respond['text'] = self.get_info_group(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == self._COMMANDS[6]:
                if(weather_command):
                    try:
                        respond['text'] = get_weather(message[1])
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                else:
                    respond['text'] = errors_array["command_off"]

            elif message[0] == self._COMMANDS[7]:
                try:
                    respond['text'] = self.wiki_article(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == self._COMMANDS[8]:
                respond['text'] = self.exchange_rates()

            elif message[0] == self._COMMANDS[9]:
                respond['text'] = "Теперь бот работает в режиме эхо. Чтобы это выключить, введить \"!echo off\""
                self.change_await("echo")
                log(False, f"[BOT_{self._CHAT_ID}] Enter in echo mode")

            elif message[0] == self._COMMANDS[10]:
                try:
                    message[1] = message[1].lower()
                    respond['text'] = self.game(message[1], user_id)
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == self._COMMANDS[11]:
                if self._ACCESS_TO_ALL or int(user_id) == int(config.owner_id):
                    try:
                        respond['text'] = self.debug(message[1])
                    except IndexError:
                        respond['text'] = self.debug()
                else:
                    respond["text"] = errors_array["access"]

            elif message[0] == self._COMMANDS[12]:
                if self._ACCESS_TO_ALL or int(user_id) == int(config.owner_id):
                    if self._MIDNIGHT_EVENT:
                        self.change_flag('midnight', False)
                        self.send("Уведомление о миднайте выключено")
                        log(False,
                            f"[BOT_{self._CHAT_ID}] Unsubscribed from event \"Midnight\"")
                    else:
                        self.change_flag('midnight', True)
                        self.send("Бот будет уведомлять вас о каждом миднайте")
                        log(False,
                            f"[BOT_{self._CHAT_ID}] Subscribed on event \"Midnight\"")
                else:
                    respond['text'] = errors_array["access"]

            elif message[0] == self._COMMANDS[13]:
                if int(user_id) == int(config.owner_id):
                    try:
                        if message[1] == "owner":
                            respond['text'] = "Теперь некоторыми командами может пользоваться только владелец бота"
                            self._ACCESS_TO_ALL = False
                        elif message[1] == "all":
                            respond['text'] = "Теперь все могут пользоваться всеми командами"
                            self._ACCESS_TO_ALL = True
                        else:
                            respond['text'] = "Некорректный аргумент"
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    log(False,
                        f"[BOT_{self._CHAT_ID}] Access level changed on {self._ACCESS_TO_ALL}")
                else:
                    respond['text'] = errors_array["access"]

            elif message[0] == self._COMMANDS[14]:
                if self._OWNER or int(user_id) == int(config.owner_id):
                    self.send("Бот выключается")
                    exit(log(False, "[SHUTDOWN]"))

            elif message[0] == self._COMMANDS[15]:
                if (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)) and self._ADMIN_MODE and int(self._CHAT_ID) > 2000000000:
                    try:
                        victum = re.search(r'id\d+', message[1]) 
                        if int(victum[0][-2:]) != int(config.owner_id):
                            vk.method("messages.removeChatUser", {"chat_id": int(
                                self._CHAT_ID)-2000000000, "member_id": victum[0][-2:]})
                            log(False,
                                f"[BOT_{self._CHAT_ID}] user {victum[0]} has been kicked")
                        else:
                            log(False, f"[BOT_{self._CHAT_ID}] can't kick owner")
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    except Exception as e:
                        respond['text'] = f"Ошибка: {str(e)}"
                        log(True,
                            f"[BOT_{self._CHAT_ID}] can't kick user {victum[0]} - {str(e)}")
                else:
                    if int(self._CHAT_ID) <= 2000000000:
                        respond['text'] = "Данный чат не является беседой"
                    if not self._ADMIN_MODE:
                        respond["text"] = "Бот не в режиме модерирования"
                    else:
                        respond["text"] = errors_array["access"]

            elif message[0] == self._COMMANDS[16]:
                if self._ACCESS_TO_ALL or int(user_id) == int(config.owner_id):
                    if self._NEW_POST:
                        self.change_flag('new_post', False)
                        self.send("Уведомление о новом посте выключено")
                        log(False,
                            f"[BOT_{self._CHAT_ID}] Unsubscribed from new posts")
                    else:
                        self.change_flag('new_post', True)
                        self.send(
                            "Бот будет уведомлять вас о каждом новом посте")
                        log(False,
                            f"[BOT_{self._CHAT_ID}] Subscribed on new posts")
                else:
                    respond['text'] = errors_array["access"]

            elif message[0] == self._COMMANDS[17]:
                try:
                    message[1] = message[1].split(' ', 1)
                    try:
                        respond['text'] = self.random_number(
                            int(message[1][0]), int(message[1][1]))
                    except:
                        respond['text'] = self.random_number(
                            0, int(message[1][0]))
                except:
                    respond['text'] = self.random_number(0, 10)

            elif message[0] == self._COMMANDS[18]:
                if int(self._CHAT_ID) <= 2000000000:
                    respond['text'] = "Данный чат не является беседой"
                elif int(user_id) != int(config.owner_id):
                    respond['text'] = errors_array["access"]
                else:
                    try:
                        vk.method("messages.getConversationMembers", {
                                  "peer_id": int(self._CHAT_ID), "group_id": config.group_id})
                        if self._ADMIN_MODE:
                            respond["text"] = "Режим модерирования выключен"
                            self.change_flag('admin_mode', False)
                            log(False,
                                f"[BOT_{self._CHAT_ID}] Admin mode: {self._ADMIN_MODE}")
                        else:
                            respond["text"] = "Режим модерирования включён"
                            self.change_flag('admin_mode', True)
                            log(False,
                                f"[BOT_{self._CHAT_ID}] Admin mode: {self._ADMIN_MODE}")
                    except Exception:
                        respond["text"] = "У меня нет прав администратора"
            
            elif message[0] == self._COMMANDS[19]: #бот не может восстанавливать пользователя из беседы, соре
                if (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)) and self._ADMIN_MODE:
                    try:
                        victum = re.search(r'id\d+', message[1]) 
                        if int(victum[0][-2:]) != int(config.owner_id):
                            vk.method("messages.addChatUser", {"chat_id": int(
                                self._CHAT_ID)-2000000000, "user_id": victum[0][-2:]})
                            log(False,
                                f"[BOT_{self._CHAT_ID}] user {victum[0]} has been kicked")
                        else:
                            log(False, f"[BOT_{self._CHAT_ID}] can't kick owner")
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    except Exception as e:
                        respond['text'] = f"Ошибка: {str(e)}"
                        log(True,
                            f"[BOT_{self._CHAT_ID}] can't kick user {victum[0]} - {str(e)}")
                else:
                    if int(self._CHAT_ID) <= 2000000000:
                        respond['text'] = "Данный чат не является беседой"
                    if not self._ADMIN_MODE:
                        respond["text"] = "Бот не в режиме модерирования"
                    else:
                        respond["text"] = errors_array["access"]

            if respond['text'] or respond['attachment']:
                self.send(respond['text'], respond['attachment'])

    def debug(self, arg=None):
        if arg == "log":
            if self._OWNER:
                with open(log_path, 'r') as f:
                    log = list(deque(f, 10))
                    text_log = "<br>Последние 10 строк из лога:<br>"
                    for i in range(len(log)):
                        text_log += log[i]
                    f.close()
                return text_log
            else:
                return errors_array["access"]
        elif arg == "bots":
            if self._OWNER:
                answer = "Обьекты бота:"
                for i in bot:
                    answer += "<br>"+str(bot[i])
                return answer
            else:
                return errors_array["access"]
        elif arg == "game":
            stats = db.get_game_stat()
            if len(stats) > 0:
                answer = "Статистика игроков в !game"
                for i in stats:
                    try:
                        winrate = (i['game_wins']/(i['game_wins'] +
                                                   i['game_defeats']+i['game_draws'])) * 100
                    except ZeroDivisionError:
                        winrate = 0
                    answer += f"<br> @id{i['chat_id']} - Сыграл раз: {i['game_wins']+i['game_defeats']+i['game_draws']}, Победы/Ничьи/Поражения: {i['game_wins']}/{i['game_draws']}/{i['game_defeats']}, {toFixed(winrate, 2)}% побед"
            else:
                answer = "Никто не пользуется !game"
            return answer
        else:
            up_time = time.time() - debug_array['start_time']
            time_d = int(up_time) / (3600 * 24)
            time_h = int(up_time) / 3600 - int(time_d) * 24
            time_min = int(up_time) / 60 - int(time_h) * \
                60 - int(time_d) * 24 * 60
            time_sec = int(up_time) - int(time_min) * 60 - \
                int(time_h) * 3600 - int(time_d) * 24 * 60 * 60
            str_up_time = '%01d:%02d:%02d:%02d' % (
                time_d, time_h, time_min, time_sec)
            datetime_time = datetime.datetime.fromtimestamp(
                debug_array['start_time'])
            answer = "UPTIME: " + str_up_time + "<br>Прослушано сообщений: " + str(
                debug_array['messages_get']) + "<br>Отправлено сообщений: " + str(
                debug_array['messages_answered']) + "<br>Ошибок в работе: " + str(
                debug_array['logger_warnings']) + ", из них:<br> •Беды с ВК: " + str(
                debug_array['vk_warnings']) + "<br> •Беды с БД: " + str(
                debug_array['db_warnings']) + "<br> •Беды с ботом: " + str(
                debug_array['bot_warnings']) + "<br>Обьектов бота: " + str(
                len(bot)) + "<br>Запуск бота по часам сервера: " + datetime_time.strftime('%d.%m.%Y %H:%M:%S UTC')
            return answer

    def game(self, thing, user_id):
        data = db.get_from_users(user_id)
        if (config.use_database):
            if len(data) == 0:
                create_new_bot_object(user_id)
                data = db.get_from_users(user_id)
            d = data[0]
        else:
            d = data
        if thing == "статистика":
            try:
                winrate = (d['game_wins']/(d['game_wins'] +
                                           d['game_defeats']+d['game_draws'])) * 100
            except ZeroDivisionError:
                winrate = 0
            return f"Камень, ножницы, бумага<br>Сыграно игр: {d['game_wins']+d['game_defeats']+d['game_draws']}<br>Из них:<br>•Побед: {d['game_wins']}<br>•Поражений: {d['game_defeats']}<br>•Ничей: {d['game_draws']}<br>Процент побед: {toFixed(winrate, 2)}%"
        elif thing == "камень" or thing == "ножницы" or thing == "бумага":
            things = ["камень", "ножницы", "бумага"]
            bot_thing = random.choice(things)
            if thing == "камень" and bot_thing == "ножницы":
                result = 2
            elif thing == "ножницы" and bot_thing == "бумага":
                result = 2
            elif thing == "бумага" and bot_thing == "камень":
                result = 2
            elif thing == "ножницы" and bot_thing == "камень":
                result = 1
            elif thing == "бумага" and bot_thing == "ножницы":
                result = 1
            elif thing == "камень" and bot_thing == "бумага":
                result = 2
            elif thing == "камень" and bot_thing == "камень":
                result = 0
            elif thing == "ножницы" and bot_thing == "ножницы":
                result = 0
            elif thing == "бумага" and bot_thing == "бумага":
                result = 0

            if result == 2:
                response = f"Камень, ножницы, бумага<br>{thing} vs. {bot_thing}<br>Вы выиграли!"
                db.update_user(user_id, "game_wins", d['game_wins']+1)
            elif result == 1:
                response = f"Камень, ножницы, бумага<br>{thing} vs. {bot_thing}<br>Вы проиграли!"
                db.update_user(user_id, "game_defeats", d['game_defeats']+1)
            elif result == 0:
                response = f"Камень, ножницы, бумага<br>{thing} vs. {bot_thing}<br>Ничья!"
                db.update_user(user_id, "game_draws", d['game_draws']+1)

            return response
        else:
            return "Неверный аргумент<br>Использование команды:<br>!game *камень/ножницы/бумага/статистика*"

    def get_info_user(self, id):
        try:
            user_info = vk.method(
                'users.get', {'user_ids': id, 'fields': 'verified,last_seen,sex'})
        except vk_api.exceptions.ApiError as lol:
            err = "Method users.get: " + str(lol)
            log(True, err)
            return "Пользователь не найден<br>" + str(lol)

        if "deactivated" in user_info[0]:
            if user_info[0]['deactivated'] == 'banned':
                return user_info[0]['first_name'] + " " + user_info[0]['last_name'] + " забанен"
            elif user_info[0]['deactivated'] == 'deleted':
                return "Профиль был удалён"

        if user_info[0]['is_closed']:
            is_closed = "Да"
        else:
            is_closed = "Нет"

        if user_info[0]['sex'] == 1:
            sex = "Женский"
        elif user_info[0]['sex'] == 2:
            sex = "Мужской"
        else:
            sex = "Неизвестно"

        if user_info[0]['last_seen']['platform'] == 1:
            platform = "m.vk.com"
        elif user_info[0]['last_seen']['platform'] == 2:
            platform = "iPhone"
        elif user_info[0]['last_seen']['platform'] == 3:
            platform = "iPad"
        elif user_info[0]['last_seen']['platform'] == 4:
            platform = "Android"
        elif user_info[0]['last_seen']['platform'] == 5:
            platform = "Windows Phone"
        elif user_info[0]['last_seen']['platform'] == 6:
            platform = "Windows 10"
        elif user_info[0]['last_seen']['platform'] == 7:
            platform = "vk.com"
        else:
            platform = "тип платформы неизвестен"

        time = datetime.datetime.fromtimestamp(
            user_info[0]['last_seen']['time'])

        answer = user_info[0]['first_name'] + " " + user_info[0]['last_name'] + "<br>Его ид: " + \
            str(user_info[0]['id']) + "<br>Профиль закрыт: " + is_closed + "<br>Пол: " + sex \
            + "<br>Последний онлайн: " + \
            time.strftime('%d.%m.%Y в %H:%M:%S') + " (" + platform + ")"

        return answer

    def get_info_group(self, id):
        try:
            group_info = vk.method(
                'groups.getById', {'group_id': id, 'fields': 'description,members_count'})
        except vk_api.exceptions.ApiError as lol:
            err = "Method groups.getById: " + str(lol)
            log(True, err)
            return "Группа не найдена<br>" + str(lol)

        if group_info[0]['description'] == "":
            description = "Отсутствует"
        else:
            description = group_info[0]['description']

        answer = group_info[0]['name'] + "<br>Описание: " + description + "<br>Ид группы: " + str(
            group_info[0]['id']) + "<br>Подписчиков: " + str(group_info[0]['members_count'])
        return answer

    def random_image(self):
        group = "-" + str(config.group_id)
        random_images_query = vk_mda.method('photos.get',
                                            {'owner_id': group, 'album_id': config.album_for_command, 'count': 1000})
        info = "Method photos.get: " + \
            str(random_images_query['count']) + " photos received"
        log(False, info)
        random_number = random.randrange(random_images_query['count'])
        return "photo" + str(random_images_query['items'][random_number]['owner_id']) + "_" + str(
            random_images_query['items'][random_number]['id'])

    def wiki_article(self, search):
        w = wiki.Wikipedia('ru')
        page = w.page(search)
        if page.exists():
            answer = page.title + "<br>" + page.summary
        else:
            answer = "Такой статьи не существует"
        return answer

    def exchange_rates(self):
        try:
            rates_USD = json.loads(
                requests.get("https://www.nbrb.by/api/exrates/rates/145?periodicity=0", timeout=10).text)
            rates_EUR = json.loads(
                requests.get("https://www.nbrb.by/api/exrates/rates/292?periodicity=0", timeout=10).text)
            rates_RUB = json.loads(
                requests.get("https://www.nbrb.by/api/exrates/rates/298?periodicity=0", timeout=10).text)
            return "Текущий курс валют по данным НБ РБ:<br>" + rates_USD['Cur_Name'] + ": " + str(
                rates_USD['Cur_Scale']) + " " + rates_USD['Cur_Abbreviation'] + " = " + str(
                rates_USD['Cur_OfficialRate']) + " BYN<br>" + rates_EUR['Cur_Name'] + ": " + str(
                rates_EUR['Cur_Scale']) + " " + rates_EUR['Cur_Abbreviation'] + " = " + str(
                rates_EUR['Cur_OfficialRate']) + " BYN<br>" + "Российский рубль" + ": " + str(
                rates_RUB['Cur_Scale']) + " " + rates_RUB['Cur_Abbreviation'] + " = " + str(
                rates_RUB['Cur_OfficialRate']) + " BYN"
        except Exception as mda:
            err = "НБ РБ API: " + str(mda)
            log(True, err)
            return "Невозможно получить данные из НБ РБ: " + str(mda)

    def random_number(self, lower, higher):
        r = random.randint(lower, higher)
        return f"Рандомное число от {lower} до {higher}:<br>{r}"

    def change_await(self, awaiting=None):
        """Change the awaiting input state

        Keyword arguments:
        awaiting -- name of function, what awaiting input from user. Defalt: None. String
        """
        self._AWAITING_INPUT_MODE = awaiting
        db.update_user(self._CHAT_ID, "awaiting", self._AWAITING_INPUT_MODE)

    def change_flag(self, flag, value):
        """Change 'flag' to 'value'
        
        Keyword arguments:
        flag -- name of flag. Can be 'access', 'new_post', 'midnight', 'admin_mode'. String
        value -- set the flag state. Bool
        """
        if flag == 'access':
            self._ACCESS_TO_ALL = value
            db.update_user(self._CHAT_ID, "access", self._ACCESS_TO_ALL)
        elif flag == 'new_post':
            self._NEW_POST = value
            db.update_user(self._CHAT_ID, "new_post", self._NEW_POST)
        elif flag == 'midnight':
            self._MIDNIGHT_EVENT = value
            db.update_user(self._CHAT_ID, "midnight", self._MIDNIGHT_EVENT)
        elif flag == 'admin_mode':
            self._ADMIN_MODE = value
            db.update_user(self._CHAT_ID, "admin_mode", self._ADMIN_MODE)

    def send(self, message=None, attachment=None):
        """Send to user something.

        Keyword arguments:
        message -- text of message. string
        attachment -- name of attachment. string
        """
        try:
            random_id = random.randint(-9223372036854775808,
                                       9223372036854775807)
            message = vk.method('messages.send',
                                {'peer_id': self._CHAT_ID, 'message': message, 'random_id': random_id,
                                 'attachment': attachment})
            log(False,
                f'[BOT_{self._CHAT_ID}] id: {message}, random_id: {random_id}')
            debug_array['messages_answered'] += 1
        except Exception as e:
            log(True, f'Failed to send message: {str(e)}')
