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
import wikipediaapi as wiki
import config
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
SPAMMER_LIST = []
errors_array = {"access": "Отказано в доступе",
                "miss_argument": "Отсуствует аргумент", 
                "command_off": "Команда отключена",
                "not_a_multichat": "Данный чат не является беседой"}

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
        try:
            with open("data.json", "r") as data:
                self._DATA_DIST = json.load(data)
                data.close()
        except Exception:
            log(True, "data.json is not exist, it will be created")
            self._DATA_DIST = {"users": {}, "spammers": []}
            open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def set_new_user(self, peer_id, midnight=False, awaiting=None, access=1, new_post=False, admin_mode=False, game_wins=0, game_defeats=0, game_draws=0, banned=False):
        self._DATA_DIST['users'][peer_id] = {"awaiting": awaiting, "access": access, "midnight": midnight, "new_post": new_post, "admin_mode": admin_mode, "game_wins": game_wins, "game_defeats": game_defeats, "game_draws": game_draws, "banned": banned, "warns": 0}
        open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def get_all_users(self):
        with open("data.json", "r") as data:
            self._DATA_DIST = json.load(data)
            data.close()
        return self._DATA_DIST['users']

    def get_from_users(self, from_id):
        with open("data.json", "r") as data:
            self._DATA_DIST = json.load(data)
            data.close()
        if not self._DATA_DIST['users'].get(str(from_id)):
            self.set_new_user(str(from_id))
        return self._DATA_DIST['users'][str(from_id)]

    def update_user(self, chat_id, thing, new_value):        
        self._DATA_DIST['users'][str(chat_id)][thing] = new_value
        open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def delete_user(self, chat_id):
        self._DATA_DIST['users'].pop(str(chat_id))
        open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def add_spammer(self, user_id):
        SPAMMER_LIST.append(int(user_id))
        self._DATA_DIST["spammers"].append(int(user_id))
        open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def remove_spammer(self, user_id):
        SPAMMER_LIST.remove(int(user_id))
        self._DATA_DIST["spammers"].remove(int(user_id))
        open("data.json", "w").write(json.dumps(self._DATA_DIST))

    def read_spammers(self):
        return self._DATA_DIST["spammers"]


db = Database_worker()



def toFixed(numObj, digits=0):
    return f"{numObj:.{digits}f}"


class MyVkLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try:
                yield from self.check()
            except Exception as e:
                err = f"A problem with VK LongPull: {str(e)}"
                log(True, err)
                debug_array['vk_warnings'] += 1
                time.sleep(15)
                continue


def get_weather(place):
    try:
        weather_request = mgr.weather_at_place(place)
    except Exception as i:
        err = f"A problem with OpenWeather API: {str(i)}"
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
    
    def __init__(self, peer_id):
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
        db_entry = db.get_from_users(int(peer_id))
        self._CHAT_ID = peer_id
        self._AWAITING_INPUT_MODE = db_entry['awaiting']
        self._ACCESS_TO_ALL = bool(db_entry['access'])
        self._MIDNIGHT_EVENT = bool(db_entry['midnight'])
        self._NEW_POST = bool(db_entry['new_post'])
        self._ADMIN_MODE = bool(db_entry['admin_mode'])
        self._BANNED = bool(db_entry['banned'])
        self._OWNER = int(self._CHAT_ID) == int(config.owner_id)
        self._COMMANDS = ["!image", "!my_id", "!h", "!help", "!user_id", "!group_id", "!weather", "!wiki", "!byn", "!echo", "!game", 
                          "!debug", "!midnight", "!access", "!turnoff", "!ban", "!subscribe", "!random", "!admin_mode", "!resist", "!restore",
                          "!картинка", "!ид", "!п", "!помощь", "!пользователь", "!группа", "!погода", "!вики", "!белруб", "!эхо", "!игра",
                          "!дебаг", "!полночь", "!доступ", "!выкл", "!бан", "!подписаться", "!рандом", "!админмод", "!запретить", "!разрешить"]

    def __str__(self):
        return f"[BOT_{str(self._CHAT_ID)}] a: {str(self._ACCESS_TO_ALL)}, mn: {str(self._MIDNIGHT_EVENT)}, await: {str(self._AWAITING_INPUT_MODE)}, sub: {str(self._NEW_POST)}, adm: {str(self._ADMIN_MODE)}, ban: {str(self._BANNED)}"

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
            self.send("Вышел новый пост", post)
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
                    if int(action["member_id"]) in SPAMMER_LIST:
                        self.send(f'[id{action["member_id"]}|Данный пользователь] находится в антиспам базе. Исключаю...')
                        vk.method("messages.removeChatUser", {"chat_id": int(self._CHAT_ID)-2000000000, "member_id": action["member_id"]})
                        return
                    self.send(f'Добро пожаловать в беседу, {user_info[0]["first_name"]} {user_info[0]["last_name"]}')
                elif action['type'] == 'chat_kick_user':
                    pass
                    # user_info = vk.method('users.get', {'user_ids': action["member_id"], 'fields': 'verified,last_seen,sex'})
                    # self.send(f'{user_info[0]["first_name"]} {user_info[0]["last_name"]} покинул беседу')
            if event.message.peer_id > 2000000000 and int(user_id) in SPAMMER_LIST:
                self.send(f'[id{user_id}|Данный пользователь] находится в антиспам базе. Исключаю...')
                vk.method("messages.removeChatUser", {"chat_id": int(self._CHAT_ID)-2000000000, "member_id": user_id})
                return
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

            if (self._BANNED or db.get_from_users(int(event.message.from_id))["banned"]) and message[0] in self._COMMANDS:
                respond['text'] = "Вам запрещено использовать бота"

            elif message[0] == "!image" or message[0] == "!картинка":
                if(random_image_command):
                    respond['attachment'] = self.random_image()
                else:
                    respond['text'] = errors_array["command_off"]

            elif message[0] == "!my_id" or message[0] == "!ид":
                respond['text'] = "Ваш ид: " + str(user_id)

            elif message[0] in ["!h", "!help", "!п", "!помощь"]:
                with open('help.txt', 'r') as h:
                    help = h.read()
                    respond['text'] = help
                    h.close()

            elif message[0] == "!user_id" or message[0] == "!пользователь":
                try:
                    respond['text'] = self.get_info_user(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == "!group_id" or message[0] == "!группа":
                try:
                    respond['text'] = self.get_info_group(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == "!weather" or message[0] == "!погода":
                if(weather_command):
                    try:
                        respond['text'] = get_weather(message[1])
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                else:
                    respond['text'] = errors_array["command_off"]

            elif message[0] == "!wiki" or message[0] == "!вики":
                try:
                    respond['text'] = self.wiki_article(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == "!byn" or message[0] == "!белруб":
                respond['text'] = self.exchange_rates()

            elif message[0] == "!echo" or message[0] == "!эхо":
                respond['text'] = "Теперь бот работает в режиме эхо. Чтобы это выключить, введить \"!echo off\""
                self.change_await("echo")
                log(False, f"[BOT_{self._CHAT_ID}] Enter in echo mode")

            elif message[0] == "!game" or message[0] == "!игра":
                try:
                    message[1] = message[1].lower()
                    respond['text'] = self.game(message[1], user_id)
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

            elif message[0] == "!debug" or message[0] == "!дебаг":
                if (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)):
                    try:
                        respond['text'] = self.debug(message[1])
                    except IndexError:
                        respond['text'] = self.debug()
                else:
                    respond["text"] = errors_array["access"]

            elif message[0] == "!midnight" or message[0] == "!полночь":
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

            elif message[0] == "!access" or message[0] == "!доступ":
                if int(user_id) == int(config.owner_id):
                    try:
                        if message[1] == "owner" or message[1] == "владелец":
                            respond['text'] = "Теперь некоторыми командами может пользоваться только владелец бота"
                            self._ACCESS_TO_ALL = False
                        elif message[1] == "all" or message[1] == "все":
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

            elif message[0] == "!turnoff" or message[0] == "!выкл":
                if self._OWNER or int(user_id) == int(config.owner_id):
                    self.send("Бот выключается")
                    exit(log(False, "[SHUTDOWN]"))

            elif message[0] == "!ban" or message[0] == "!бан":
                if (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)) and self._ADMIN_MODE and int(self._CHAT_ID) > 2000000000:
                    try:
                        victum = re.search(r'id\d+', message[1])
                        victum = victum[0][2:]
                        if int(victum) != int(config.owner_id):
                            vk.method("messages.removeChatUser", {"chat_id": int(self._CHAT_ID)-2000000000, "member_id": victum})
                            log(False, f"[BOT_{self._CHAT_ID}] user {victum} has been kicked")
                        else:
                            log(False, f"[BOT_{self._CHAT_ID}] can't kick owner")
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    except Exception as e:
                        respond['text'] = f"Ошибка: {str(e)}"
                        log(True,
                            f"[BOT_{self._CHAT_ID}] can't kick user {victum} - {str(e)}")
                else:
                    if int(self._CHAT_ID) <= 2000000000:
                        respond['text'] = errors_array["not_a_multichat"]
                    if not self._ADMIN_MODE:
                        respond["text"] = "Бот не в режиме модерирования"
                    else:
                        respond["text"] = errors_array["access"]

            elif message[0] == "!subscribe" or message[0] == "!подписаться":
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

            elif message[0] == "!random" or message[0] == "!рандом":
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

            elif message[0] == "!admin_mode" or message[0] == "!админмод":
                if int(self._CHAT_ID) <= 2000000000:
                    respond['text'] = errors_array["not_a_multichat"]
                elif int(user_id) != int(config.owner_id):
                    respond['text'] = errors_array["access"]
                else:
                    try:
                        vk.method("messages.getConversationMembers", {
                                  "peer_id": int(self._CHAT_ID), "group_id": config.group_id})
                        if self._ADMIN_MODE:
                            respond["text"] = "Режим модерирования выключен"
                            self.change_flag('admin_mode', False)
                            log(False, f"[BOT_{self._CHAT_ID}] Admin mode: {self._ADMIN_MODE}")
                        else:
                            respond["text"] = "Режим модерирования включён"
                            self.change_flag('admin_mode', True)
                            log(False, f"[BOT_{self._CHAT_ID}] Admin mode: {self._ADMIN_MODE}")
                    except Exception as e:
                        respond["text"] = f"Ошибка: {str(e)}"
            
            elif message[0] == "!resist" or message[0] == "!запретить":
                if (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)):
                    try:
                        victum = re.search(r'id\d+', message[1])
                        victum = victum[0][2:]
                        if int(victum) != int(config.owner_id):
                            if int(victum) not in bot:
                                bot[user_id] = VkBot(int(victum))
                                db.set_new_user(int(victum))
                            if not db.get_from_users(int(victum))["banned"]:
                                bot[int(victum)].change_flag("banned", True)
                                respond["text"] = "Теперь он не сможет воспользоваться ботом"
                                log(False, f"[BOT_{self._CHAT_ID}] user {victum} has been resisted")
                            else:
                                respond["text"] = "Он и так не может пользоваться ботом, вы уже делали это"
                        else:
                            log(False, f"[BOT_{self._CHAT_ID}] can't resist owner")
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    except Exception as e:
                        respond['text'] = f"Ошибка: {str(e)}"
                        log(True,
                            f"[BOT_{self._CHAT_ID}] can't resist user {victum} - {str(e)}")
                else:
                    respond["text"] = errors_array["access"]

            elif message[0] == "!restore" or message[0] == "!разрешить":
                if (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)):
                    try:
                        victum = re.search(r'id\d+', message[1])
                        victum = victum[0][2:]
                        if int(victum) not in bot:
                            bot[user_id] = VkBot(int(victum))
                            db.set_new_user(int(victum))
                        if int(victum) != int(config.owner_id):
                            if db.get_from_users(int(victum))["banned"]:
                                bot[int(victum)].change_flag("banned", False)
                                respond["text"] = "Теперь он снова сможет воспользоваться ботом"
                                log(False, f"[BOT_{self._CHAT_ID}] user {victum} has been restored")
                            else:
                                respond["text"] = "Он и так может пользоваться ботом"
                        else:
                            log(False, f"[BOT_{self._CHAT_ID}] can't restore owner")
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    except Exception as e:
                        respond['text'] = f"Ошибка: {str(e)}"
                        log(True,
                            f"[BOT_{self._CHAT_ID}] can't restore user {victum} - {str(e)}")
                else:
                    respond["text"] = errors_array["access"]

            elif message[0] == "!spammer" or message[0] == "!спаммер":
                if int(self._CHAT_ID) <= 2000000000:
                    respond['text'] = errors_array["not_a_multichat"]
                elif (self._OWNER or int(user_id) in config.admins or int(user_id) == int(config.owner_id)):
                    try:
                        message = message[1].split(' ', 1)
                        victum = re.search(r'id\d+', message[1])
                        victum = victum[0][2:]
                        if message[0] == "add" or message[0] == "добавить":
                            if int(victum) != int(config.owner_id):
                                if int(victum) not in SPAMMER_LIST:
                                    db.add_spammer(int(victum))
                                    respond["text"] = "Теперь он считается спамером"
                                    log(False, f"[BOT_{self._CHAT_ID}] user {victum} added to spammer list")
                                    for i in bot:
                                        if i > 2000000000:
                                            bot[i].kick_spammers()
                                else:
                                    respond["text"] = "Он и так уже в этой базе"  
                            else:
                                log(False, f"[BOT_{self._CHAT_ID}] can't add to spammer list owner")
                        elif message[0] == "remove" or message[0] == "удалить":
                            if int(victum) != int(config.owner_id):
                                if int(victum) in SPAMMER_LIST:
                                    db.remove_spammer(int(victum))
                                    respond["text"] = "Теперь он не считается спамером"
                                    log(False, f"[BOT_{self._CHAT_ID}] user {victum} removed to spammer list")
                                else:
                                    respond["text"] = "Его нет в этой базе"  
                            else:
                                log(False, f"[BOT_{self._CHAT_ID}] can't restore owner")
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    except Exception as e:
                        respond['text'] = f"Ошибка: {str(e)}"
                        log(True, f"[BOT_{self._CHAT_ID}] spammer action {message[1]} with {victum} - {str(e)}")

            if respond['text'] or respond['attachment']:
                self.send(respond['text'], respond['attachment'])

    def debug(self, arg=None):
        if arg in ["log", "лог"]:
            if not self._OWNER:
                return errors_array["access"]
            with open(log_path, 'r') as f:
                log = list(deque(f, 10))
                text_log = "<br>Последние 10 строк из лога:<br>"
                for item in log:
                    text_log += item
                f.close()
            return text_log
        elif arg in ["bots", "боты"]:
            if not self._OWNER:
                return errors_array["access"]
            answer = "Обьекты бота:"
            for i in bot:
                answer += f"<br>{str(bot[i])}"
            return answer
        elif arg in ["game", "игра"]:
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
            answer = (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            f"UPTIME: {str_up_time}<br>Прослушано сообщений: "
                                            + str(debug_array['messages_get'])
                                        )
                                        + "<br>Отправлено сообщений: "
                                    )
                                    + str(debug_array['messages_answered'])
                                    + "<br>Ошибок в работе: "
                                )
                                + str(debug_array['logger_warnings'])
                                + ", из них:<br> •Беды с ВК: "
                            )
                            + str(debug_array['vk_warnings'])
                            + "<br> •Беды с БД: "
                        )
                        + str(debug_array['db_warnings'])
                        + "<br> •Беды с ботом: "
                    )
                    + str(debug_array['bot_warnings'])
                    + "<br>Обьектов бота: "
                )
                + str(len(bot))
                + "<br>Запуск бота по часам сервера: "
            ) + datetime_time.strftime('%d.%m.%Y %H:%M:%S UTC')

            return answer

    def game(self, thing, user_id):
        d = db.get_from_users(user_id)
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
        elif flag == "banned":
            self._BANNED = value
            db.update_user(self._CHAT_ID, "banned", self._BANNED)

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

    def kick_spammers(self):
        if self._CHAT_ID > 2000000000 and self._ADMIN_MODE:
            peer_users_list = vk.method("messages.getConversationMembers", {"peer_id": int(self._CHAT_ID), "group_id": config.group_id})
            for i in peer_users_list["items"]:
                if i['member_id'] in SPAMMER_LIST:
                    self.send(f'[id{i["member_id"]}|Данный пользователь] находится в антиспам базе. Исключаю...')
                    vk.method("messages.removeChatUser", {"chat_id": int(self._CHAT_ID)-2000000000, "member_id": i['member_id']})
