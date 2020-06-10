import vk_api
import datetime
import time
import requests
import logging
import pyowm
import random
import json
import threading
import pymysql
from pymysql.cursors import DictCursor
import wikipediaapi as wiki
from collections import deque
from config import vk, owm, vk_mda, group_id, album_for_command, owner_id, mysql_host, mysql_pass, mysql_user, mysql_db
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

log(False, "Script started")

bot = {}
debug_array = {'vk_warnings': 0, 'db_warnings': 0, 'bot_warnings': 0, 'logger_warnings': 0, 'start_time': 0, 'messages_get': 0, 'messages_answered': 0}
errors_array = {"access": "Отказано в доступе", "miss_argument": "Отсуствует аргумент"}

longpoll = VkBotLongPoll(vk, group_id)

class MySQL_worker():
    
    def __init__(self):
        try:
            self._CON = pymysql.connect(
                host= mysql_host,
                user= mysql_user,
                password= mysql_pass,
                db= mysql_db,
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            cur = self._CON.cursor()
            try:
                cur.execute("SELECT * FROM bot_users")
            except:
                cur.execute("CREATE TABLE bot_users ( id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, chat_id INT UNSIGNED, awaiting VARCHAR(128), access TINYINT, midnight BOOL, new_post BOOL, admin_mode BOOL, game_wins INT UNSIGNED, game_defeats INT UNSIGNED, game_draws INT UNSIGNED)")
            try:
                cur.execute("SELECT * FROM tasks")
            except:
                cur.execute("CREATE TABLE tasks (id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, chat_id INT UNSIGNED, time INT UNSIGNED, task TEXT)")
            cur.close()
            log(False, f"Database connection established")
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to connect to database: {str(e)}")
            
    def set_new_user(self, peer_id, midnight=False, awaiting=None, access=1, new_post=False, admin_mode=False, game_wins=0, game_defeats=0, game_draws=0):
        try:
            cur = self._CON.cursor()
            cur.execute("INSERT INTO bot_users (chat_id, awaiting, access, midnight, new_post, admin_mode, game_wins, game_defeats, game_draws) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (peer_id, awaiting, access, midnight, new_post, admin_mode, game_wins, game_defeats, game_draws))
            self._CON.commit()
            cur.close()
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to add new user in database: {str(e)}")
    
    def get_all_users(self):
        try:
            cur = self._CON.cursor()
            cur.execute("SELECT * FROM bot_users")
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to load user from database: {str(e)}")

    def get_from_users(self, from_id):
        try:
            cur = self._CON.cursor()
            cur.execute("SELECT * FROM bot_users WHERE chat_id = %s", (from_id))
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to load user from database: {str(e)}")

    def get_game_stat(self):
        try:
            cur = self._CON.cursor()
            cur.execute("SELECT chat_id, game_wins, game_draws, game_defeats FROM bot_users WHERE game_wins > 0 OR game_draws > 0 OR game_defeats > 0")
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to load stats from database: {str(e)}")
    
    def update_user(self, chat_id, thing, new_value):
        try:
            cur = self._CON.cursor()
            cur.execute(f"UPDATE bot_users SET {thing} = %s WHERE bot_users.chat_id = %s;", (new_value, chat_id))
            self._CON.commit()
            cur.close()
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to update info about user in database: {str(e)}")

    def delete_user(self, chat_id):
        try:
            cur = self._CON.cursor()
            cur.execute("DELETE FROM bot_users, game_defeats WHERE chat_id = %s", (chat_id))
            self._CON.commit()
            cur.close()
            return True
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to delete user from database: {str(e)}")
            return False

    def get_all_tasks(self):
        try:
            cur = self._CON.cursor()
            cur.execute("SELECT * FROM tasks")
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to load tasks from database: {str(e)}")

    def set_new_task(self, chat_id, time, task):
        try:
            cur = self._CON.cursor()
            cur.execute("INSERT INTO tasks (chat_id, time, task) VALUES (%s, %s, %s)", (chat_id, time, task))
            self._CON.commit()
            cur.close()
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to add new task in database: {str(e)}")

    def get_from_tasks(self, from_id):
        try:
            cur = self._CON.cursor()
            cur.execute("SELECT * FROM tasks WHERE chat_id = %s", (from_id))
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to load tasks from database: {str(e)}")
    
    def delete_task(self, from_id, task):
        try:
            cur = self._CON.cursor()
            cur.execute("DELETE FROM tasks WHERE chat_id = %s AND task = %s", (from_id, task))
            self._CON.commit()
            cur.close()
            return True
        except Exception as e:
            debug_array['db_warnings'] += 1
            log(True, f"Unable to delete task from database: {str(e)}")
            return False

db = MySQL_worker()

def load_users():
    try:
        log(False, "Reading database")
        get_info = db.get_all_users()
        for i in get_info:
            bot[int(i['chat_id'])] = VkBot(i['chat_id'], i['midnight'], i['awaiting'], int(i['access']), i['new_post'], i['admin_mode'])
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
        weather_request = owm.weather_at_place(place)
    except pyowm.exceptions.api_response_error.NotFoundError as i:
        err = "A problem with OpenWeather API: " + str(i)
        log(True, err)
        return "Такого города нет, либо данных о погоде нет"
    weather_answer = weather_request.get_weather()
    info = "OpenWeather API: " + str(weather_answer)
    log(False, info)
    return "В городе " + place + " сейчас " + weather_answer.get_detailed_status() + ", " + str(
        round(weather_answer.get_temperature('celsius')['temp'])) + "°C"


class VkBot:

    def __init__(self, peer_id, midnight=False, awaiting=None, access=1, new_post=False, admin_mode=False):

        log(False, f"[BOT_{peer_id}] Created new bot-object")
        self._CHAT_ID = peer_id
        self._AWAITING_INPUT_MODE = awaiting
        self._ACCESS_LEVEL = access
        self._SET_UP_REMINDER = {"task": None, "time": None}
        self._MIDNIGHT_EVENT = midnight
        self._NEW_POST = new_post
        self._ADMIN_MODE = admin_mode

        if int(self._CHAT_ID) == int(owner_id):
            self._OWNER = True
        else:
            self._OWNER = False

        self._COMMANDS = ["!image", "!my_id", "!h", "!user_id", "!group_id", "!help", "!weather", "!wiki", "!byn",
                          "!echo", "!game", "!debug", "!midnight", "!access", "!turnoff", "!reminder", "!subscribe", "!random", "!admin_mode"]

    def __str__(self):
        return f"[BOT_{str(self._CHAT_ID)}] a: {str(self._ACCESS_LEVEL)}, mn: {str(self._MIDNIGHT_EVENT)}, await: {str(self._AWAITING_INPUT_MODE)}, sub: {str(self._NEW_POST)}, adm: {str(self._ADMIN_MODE)}"

    def __del__(self):
        log(False, f"[BOT_{str(self._CHAT_ID)}] Bot-object has been deleted")

    def event(self, event, something=None):
        if event == "midnight" and self._MIDNIGHT_EVENT:
            current_time = datetime.datetime.fromtimestamp(time.time() + 10800)

            midnight_text = ["Миднайт!", "Полночь!", "Midnight!", "миднигхт", "Середина ночи", "Смена даты!"]
            # midnight_after = ["Ложись спать!", "P E A C E  A N D  T R A N Q U I L I T Y", "Поиграй в майнкрафт",
            #                   "Втыкай в ВК дальше", "hat in time is gay", "RIP 2013-2019 Gears for Breakfast", "Egg",
            #                   "вещ или бан", "Мой ник в игре _ичё", "Я жил, но что-то пошло не так",
            #                   "Когда тебе похуй, ты неувязвим", "Who's Afraid Of 138?!"]

            self.send(f"{random.choice(midnight_text)}<br>Наступило {current_time.strftime('%d.%m.%Y')}<br>Картинка дня:", self.random_image())
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
                    if int(user_id) != int(owner_id):
                        vk.method("messages.removeChatUser", {"chat_id": int(self._CHAT_ID)-2000000000, "member_id": user_id})
                        log(False, f"[BOT_{self._CHAT_ID}] user id{user_id} has been kicked")
                    else:
                        log(False, f"[BOT_{self._CHAT_ID}] can't kick owner")
                except Exception as e:
                    log(True, f"[BOT_{self._CHAT_ID}] can't kick user id{user_id} - {str(e)}")
            with open('bad_words.txt', 'r') as filter:
                flag = False
                for word in filter:
                    if flag:
                        log(False, f"[BOT_{self._CHAT_ID}] bad word detected")
                        if random.randint(1, 5) == 1:
                            self.send("За м*т извенись")
                        break
                    if message.lower().find(word) != -1:
                        flag = True
        if self._AWAITING_INPUT_MODE:
            if message == "Назад":
                self.change_await()
                self.send("Отменено")
            else:
                if self._AWAITING_INPUT_MODE == "reminder task":
                    self.reminder(message, "task")
                    self.send('Когда напомнить? (время в формате дд.мм.гг чч:мм)')
                    self.change_await('reminder time')
                elif self._AWAITING_INPUT_MODE == 'reminder time':
                    if self.reminder(message, "time"):
                        self.send("Напоминание установлено<br>Внимание: напоминание не сработает, если бот будет перезагружен")
                        self.change_await()
                    else:
                        self.send("Неверный формат времени, введите время в формате дд.мм.гг чч:мм")
                elif self._AWAITING_INPUT_MODE == "reminder delete":
                    if self.reminder(message, "delete"):
                        self.send("Напоминание удалено")
                        self.change_await()
                    else:
                        self.send("Нет такого напоминания")
                elif self._AWAITING_INPUT_MODE == "echo":
                    if message == "!echo off":
                        self.send("Эхо режим выключен")
                        self.change_await()
                        log(False, f"[BOT_{self._CHAT_ID}] Out from echo mode")
                    else:
                        self.send(message)
                        log(False, f"[BOT_{self._CHAT_ID}] Answer in echo mode")
        else:
            respond = {'attachment': None, 'text': None}
            message = message.split(' ', 1)
            if message[0] == self._COMMANDS[0]:
                respond['attachment'] = self.random_image()

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
                try:
                    respond['text'] = get_weather(message[1])
                except IndexError:
                    respond['text'] = errors_array["miss_argument"]

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
                if self._ACCESS_LEVEL or int(user_id) == int(owner_id):
                    try:
                        respond['text'] = self.debug(message[1])
                    except IndexError:
                        respond['text'] = self.debug()
                else:
                    respond["text"] = errors_array["access"]

            elif message[0] == self._COMMANDS[12]:
                if self._ACCESS_LEVEL or int(user_id) == int(owner_id):
                    if self._MIDNIGHT_EVENT:
                        self.change_midnight(False)
                        self.send("Уведомление о миднайте выключено")
                        log(False, f"[BOT_{self._CHAT_ID}] Unsubscribed from event \"Midnight\"")
                    else:
                        self.change_midnight(True)
                        self.send("Бот будет уведомлять вас о каждом миднайте")
                        log(False, f"[BOT_{self._CHAT_ID}] Subscribed on event \"Midnight\"")
                else:
                    respond['text'] = errors_array["access"]

            elif message[0] == self._COMMANDS[13]:
                if int(user_id) == int(owner_id):
                    try:
                        if message[1] == "owner":
                            respond['text'] = "Теперь некоторыми командами может пользоваться только владелец бота"
                            self.change_access(0)
                        elif message[1] == "all":
                            respond['text'] = "Теперь все могут пользоваться всеми командами"
                            self.change_access(1)
                        else:
                            respond['text'] = "Некорректный аргумент"
                    except IndexError:
                        respond['text'] = errors_array["miss_argument"]
                    log(False, f"[BOT_{self._CHAT_ID}] Access level changed on {self._ACCESS_LEVEL}")
                else:
                    respond['text'] = errors_array["access"]

            elif message[0] == self._COMMANDS[14]:
                if self._OWNER or int(user_id) == int(owner_id):
                    self.send("Бот выключается")
                    exit(log(False, "[SHUTDOWN]"))

            elif message[0] == self._COMMANDS[15]:
                try:
                    if message[1] == "list":
                        respond['text'] = self.reminder(None, "list")
                    elif message[1] == "set":
                        self.send("О чём мне вам напомнить? (Введите \"Назад\", чтобы отменить установку)")
                        self.change_await("reminder task")
                    elif message[1] == "delete":                        
                        self.send(f"Введите название напоминания, которое необходимо удалить или \"Назад\", чтобы отменить удаление<br>{self.reminder(None, 'list')}")
                        self.change_await("reminder delete")
                    else:
                        respond['text'] = "Неверный аргумент"
                except IndexError:
                    respond["text"] = errors_array['miss_argument']
            
            elif message[0] == self._COMMANDS[16]:
                if self._ACCESS_LEVEL or int(user_id) == int(owner_id):
                    if self._NEW_POST:
                        self.change_new_post(False)
                        self.send("Уведомление о новом посте выключено")
                        log(False, f"[BOT_{self._CHAT_ID}] Unsubscribed from new posts")
                    else:
                        self.change_new_post(True)
                        self.send("Бот будет уведомлять вас о каждом новом посте")
                        log(False, f"[BOT_{self._CHAT_ID}] Subscribed on new posts")
                else:
                    respond['text'] = errors_array["access"]
            
            elif message[0] == self._COMMANDS[17]:
                try:
                    message[1] = message[1].split(' ', 1)
                    try:
                        respond['text'] = self.random_number(int(message[1][0]), int(message[1][1]))
                    except:
                        respond['text'] = self.random_number(0, int(message[1][0]))
                except:
                    respond['text'] = self.random_number(0, 10)
            elif message[0] == self._COMMANDS[18]:
                if int(self._CHAT_ID) <= 2000000000:
                    respond['text'] = "Данный чат не является беседой"
                elif int(user_id) != int(owner_id):
                    respond['text'] = errors_array["access"]
                else:
                    try:
                        vk.method("messages.getConversationMembers", {"peer_id": int(self._CHAT_ID), "group_id": group_id})
                        if self._ADMIN_MODE:
                            respond["text"] = "Режим модерирования выключен"
                            self.change_admin_mode(False)
                            log(False, f"[BOT_{self._CHAT_ID}] Admin mode: {self._ADMIN_MODE}")
                        else:
                            respond["text"] = "Режим модерирования включён"
                            self.change_admin_mode(True)
                            log(False, f"[BOT_{self._CHAT_ID}] Admin mode: {self._ADMIN_MODE}")
                    except Exception:
                        respond["text"] = "У меня нет прав администратора"
                    
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
                        winrate = (i['game_wins']/(i['game_wins']+i['game_defeats']+i['game_draws'])) * 100
                    except ZeroDivisionError:
                        winrate = 0
                    answer += f"<br> @id{i['chat_id']} - Сыграл раз: {i['game_wins']+i['game_defeats']+i['game_draws']}, Победы/Ничьи/Поражения: {i['game_wins']}/{i['game_draws']}/{i['game_defeats']}, {toFixed(winrate, 2)}% побед"
            else:
                answer = "Никто не пользуется !game"
            return answer
        elif arg == "tasks":
            if self._OWNER:
                tasks = db.get_all_tasks()
                if len(tasks) > 0:
                    answer = "Напоминания в !reminder"
                    for i in tasks:
                        answer += f"<br>id{i['chat_id']} - {i['time']}: {i['task']}"
                else:
                    answer = "Никто не пользуется !reminder"
            return answer
        else:
            up_time = time.time() - debug_array['start_time']
            time_d = int(up_time) / (3600 * 24)
            time_h = int(up_time) / 3600 - int(time_d) * 24
            time_min = int(up_time) / 60 - int(time_h) * 60 - int(time_d) * 24 * 60
            time_sec = int(up_time) - int(time_min) * 60 - int(time_h) * 3600 - int(time_d) * 24 * 60 * 60
            str_up_time = '%01d:%02d:%02d:%02d' % (time_d, time_h, time_min, time_sec)
            datetime_time = datetime.datetime.fromtimestamp(debug_array['start_time'])
            answer = "UPTIME: " + str_up_time + "<br>Прослушано сообщений: " + str(
                debug_array['messages_get']) + "<br>Отправлено сообщений: " + str(
                debug_array['messages_answered']) + "<br>Ошибок в работе: " + str(
                debug_array['logger_warnings']) + ", из них:<br> •Беды с ВК: " + str(
                debug_array['vk_warnings']) + "<br> •Беды с БД: " + str(
                debug_array['db_warnings']) + "<br> •Беды с ботом: " + str(
                debug_array['bot_warnings']) + "<br>Обьектов бота: " + str(
                len(bot)) + "<br>Запуск бота по часам сервера: " + datetime_time.strftime('%d.%m.%Y %H:%M:%S UTC')
            return answer

    def reminder(self, string, stage):
        if stage == "task":
            self._SET_UP_REMINDER['task'] = string
            return True
        elif stage == "time":
            try:
                datetime_object = time.strptime(string, '%d.%m.%y %H:%M')
                self._SET_UP_REMINDER['time'] = int(time.mktime(datetime_object))
                db.set_new_task(self._CHAT_ID, self._SET_UP_REMINDER['time'], self._SET_UP_REMINDER["task"])
                log(False, f"[BOT_{self._CHAT_ID}] New reminder set")
                return True
            except ValueError:
                return False
        elif stage == "remind":
            self.send(f"Пришло время вам напомнить: {string}")
            log(False, f"[BOT_{self._CHAT_ID}] Reminder worked")
            return True
        elif stage == "list":
            tasks = db.get_from_tasks(self._CHAT_ID)
            print(tasks)
            if len(tasks) == 0:
                respond = "У вас не установлено ни одно напоминание"
            else:
                respond = 'Установленные напоминания:<br>'
                for i in tasks:
                    datetime_time = datetime.datetime.fromtimestamp(int(i['time']))
                    respond += f"<br>{datetime_time.strftime('%d.%m.%y %H:%M')} - {i['task']}"
            return respond
        elif stage == "delete":
            return db.delete_task(self._CHAT_ID, string)

    def game(self, thing, user_id):
        data = db.get_from_users(user_id)
        if len(data) == 0:
            create_new_bot_object(user_id)
            data = db.get_from_users(user_id)
        d = data[0]
        if thing == "статистика":
            try:
                winrate = (d['game_wins']/(d['game_wins']+d['game_defeats']+d['game_draws'])) * 100
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
            user_info = vk.method('users.get', {'user_ids': id, 'fields': 'verified,last_seen,sex'})
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

        time = datetime.datetime.fromtimestamp(user_info[0]['last_seen']['time'])

        answer = user_info[0]['first_name'] + " " + user_info[0]['last_name'] + "<br>Его ид: " + \
                 str(user_info[0]['id']) + "<br>Профиль закрыт: " + is_closed + "<br>Пол: " + sex \
                 + "<br>Последний онлайн: " + time.strftime('%d.%m.%Y в %H:%M:%S') + " (" + platform + ")"

        return answer

    def get_info_group(self, id):
        try:
            group_info = vk.method('groups.getById', {'group_id': id, 'fields': 'description,members_count'})
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
        group = "-" + str(group_id)
        random_images_query = vk_mda.method('photos.get',
                                            {'owner_id': group, 'album_id': album_for_command, 'count': 1000})
        info = "Method photos.get: " + str(random_images_query['count']) + " photos received"
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
        self._AWAITING_INPUT_MODE = awaiting
        db.update_user(self._CHAT_ID, "awaiting", self._AWAITING_INPUT_MODE)
    
    def change_access(self, level):
        self._ACCESS_LEVEL = level
        db.update_user(self._CHAT_ID, "access", self._ACCESS_LEVEL)

    def change_new_post(self, new_post):
        self._NEW_POST = new_post
        db.update_user(self._CHAT_ID, "new_post", self._NEW_POST)
    
    def change_midnight(self, midnight):
        self._MIDNIGHT_EVENT = midnight
        db.update_user(self._CHAT_ID, "midnight", self._MIDNIGHT_EVENT)
    
    def change_admin_mode(self, admin_mode):
        self._ADMIN_MODE = admin_mode
        db.update_user(self._CHAT_ID, "admin_mode", self._ADMIN_MODE)

    def send(self, message=None, attachment=None):
        try:
            random_id = random.randint(-9223372036854775808, 9223372036854775807)
            message = vk.method('messages.send',
                                {'peer_id': self._CHAT_ID, 'message': message, 'random_id': random_id,
                                'attachment': attachment})
            log(False, f'[BOT_{self._CHAT_ID}] id: {message}, random_id: {random_id}')
            debug_array['messages_answered'] += 1
        except Exception as e:
            log(True, f'Failed to send message: {str(e)}')
        

def bots():
    log(False, "Started listening longpull server")
    debug_array['start_time'] = time.time()
    for event in MyVkLongPoll.listen(longpoll):
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                log_msg = f'[MESSAGE] id: {event.message.id}, peer_id: {event.message.peer_id}, user_id: {event.message.from_id}'
                if event.message.text != "":
                    log_msg += f', text: "{event.message.text}"'
                if event.message.attachments:
                    atch = ', attachments: '
                    for i in event.message.attachments:
                        if i['type'] == "sticker":
                            atch += f"sticker_id{i[i['type']]['sticker_id']}"
                        elif i['type'] == "wall":
                            atch += i['type'] + str(i[i['type']]['from_id']) + "_" + str(i[i['type']]['id']) + " "
                        else:
                            atch += i['type'] + str(i[i['type']]['owner_id']) + "_" + str(i[i['type']]['id']) + " "
                    log_msg += atch
                log(False, log_msg)
                debug_array['messages_get'] += 1
                if int(event.message.peer_id) in bot:
                    bot[event.message.peer_id].get_message(event)
                else:
                    create_new_bot_object(event.message.peer_id)
                    bot[event.message.peer_id].get_message(event)
            elif event.type == VkBotEventType.WALL_POST_NEW:
                log(False, f"[NEW_POST] id{event.object.id}")
                users = db.get_all_users()
                for i in users:
                    bot[int(i['chat_id'])].event("post", event.object)
            elif event.type == VkBotEventType.MESSAGE_DENY:
                log(False, f"User {event.object.user_id} deny messages from that group")
                del bot[int(event.object.user_id)]
                db.delete_user(event.object.user_id)
            else:
                log(False, f"Event {str(event.type)} happend")
        except Exception as kek:
            log(True, f"Беды с ботом: {str(kek)}")
            debug_array['bot_warnings'] += 1
            continue

def midnight():
    while True:
        current_time = time.time()+10800
        if int(current_time) % 86400 == 0:
            log(False, "[EVENT_STARTED] \"Midnight\"")
            users = db.get_all_users()
            for i in users:
                bot[int(i['chat_id'])].event("midnight")
            log(False, "[EVENT_ENDED] \"Midnight\"")
            time.sleep(1)
        else:
            time.sleep(0.50)

def check_tasks():
    while True:
        try:
            tasks = db.get_all_tasks()
            for i in tasks:
                current_time = time.time()+10800
                if i['time'] == int(current_time):
                    bot[i['chat_id']].reminder(i['task'], "remind")
                    db.delete_task(i["chat_id"], i['task'])
        except RuntimeError:
            continue
        time.sleep(0.4)           

load_users()
tread_bots = threading.Thread(target=bots)
tread_midnight = threading.Thread(target=midnight, daemon=True)
tread_tasks = threading.Thread(target=check_tasks, daemon=True)
tread_bots.start()
tread_midnight.start()
tread_tasks.start()
