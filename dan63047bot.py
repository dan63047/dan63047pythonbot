import vk_api
import datetime
import time
import requests
import logging
import pyowm
import random
import json
import threading
import wikipediaapi as wiki
from collections import deque

from PIL import Image

from config import vk, owm, vk_mda, group_id, album_for_command, owner_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

bot = {}
users = {}
debug_array = {'vk_warnings': 0, 'logger_warnings': 0, 'start_time': 0, 'messages_get': 0, 'messages_answered': 0}
errors_array = {"access": "Отказано в доступе", "miss_argument": "Отсуствует аргумент"}

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler('bot.log', 'w', 'utf-8')
handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
root_logger.addHandler(handler)

longpoll = VkBotLongPoll(vk, group_id)


def update_users_json(massive):
    with open("users.json", 'w') as write_file:
        data = massive
        json.dump(data, write_file)
        write_file.close()


def load_users():
    try:
        with open("users.json", 'r') as users_file:
            users_not_json = json.load(users_file)
            for i in users_not_json:
                users[i] = users_not_json[i]
            users_file.close()
        for i in users:
            bot[int(i)] = VkBot(i, users[i]["midnight"], users[i]['await'], int(users[i]['access']), users[i]['new_post'])
    except Exception as lol:
        log(True, f"Problem with users.json: {str(lol)}")


def log(warning, text):
    if warning:
        logging.warning(text)
        debug_array['logger_warnings'] += 1
        print("[" + str(datetime.datetime.now()) + "] [WARNING] " + text)
    else:
        logging.info(text)
        print("[" + str(datetime.datetime.now()) + "] " + text)


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

    def __init__(self, peer_id, midnight=False, awaiting=None, access=1, new_post=False):

        log(False, f"[BOT_{peer_id}] Created new bot-object")
        self._CHAT_ID = peer_id
        self._AWAITING_INPUT_MODE = awaiting
        self._ACCESS_LEVEL = access
        self._SET_UP_REMINDER = {"task": None, "time": None}
        self._MIDNIGHT_EVENT = midnight
        self._NEW_POST = new_post

        if int(self._CHAT_ID) == int(owner_id):
            self._OWNER = True
        else:
            self._OWNER = False

        self._COMMANDS = ["!image", "!my_id", "!h", "!user_id", "!group_id", "!help", "!weather", "!wiki", "!byn",
                          "!echo", "!game", "!debug", "!midnight", "!access", "!turnoff", "!reminder", "!subscribe"]

    def __str__(self):
        return f"peer_id: {str(self._CHAT_ID)}, m: {str(self._MIDNIGHT_EVENT)}, await: {str(self._AWAITING_INPUT_MODE)}, tasks: {len(users[self._CHAT_ID]['tasks'])}"

    def __del__(self):
        log(False, f"[BOT_{str(self._CHAT_ID)}] Bot-object has been deleted")

    def event(self, event, something=None):
        if event == "midnight" and self._MIDNIGHT_EVENT:
            current_time = datetime.datetime.fromtimestamp(time.time() + 10800)
            image = None

            midnight_text = ["Миднайт!", "Полночь!", "Midnight!", "миднигхт", "Середина ночи", "Смена даты!"]
            midnight_after = ["Ложись спать!", "P E A C E  A N D  T R A N Q U I L I T Y", "Поиграй в майнкрафт",
                              "Втыкай в ВК дальше", "hat in time is gay", "RIP 2013-2019 Gears for Breakfast", "Egg",
                              "вещ или бан", "Мой ник в игре _ичё", "Я жил, но что-то пошло не так",
                              "Когда тебе похуй, ты неувязвим", "Who's Afraid Of 138?!"]

            midnight_output = random.choice(midnight_text) + "<br>" + f"Наступило {current_time.strftime('%d.%m.%Y')}<br><br>"
            random_thing = random.randint(0, 2)
            if random_thing == 0:
                midnight_output += random.choice(midnight_after)
            elif random_thing == 1:
                midnight_output += "Картинка дня:"
                image = self.random_image()
            elif random_thing == 2:
                R = random.randint(0, 255)
                G = random.randint(0, 255)
                B = random.randint(0, 255)
                random_color_image = Image.new("RGB", (512, 512), (R, G, B))
                random_color_image.save("randomcolor.jpg")
                try:
                    what_send = vk_api.upload.VkUpload(vk).photo_messages("randomcolor.jpg", peer_id=self._CHAT_ID)
                    image = "photo" + str(what_send[0]['owner_id']) + "_" + str(what_send[0]['id'])
                except Exception as e:
                    midnight_output += "Не удалось загрузить картинку с цветом<br>"
                    log(True, f"Проблема с отправкой картинки цвета: {str(e)}")
                midnight_output += "Цвет дня в формате HEX: #%02x%02x%02x" % (R, G, B)

            self.send(midnight_output, image)
            log(False, f"[BOT_{self._CHAT_ID}] Notified about midnight")
        elif event == "post" and self._NEW_POST:
            post = f"wall{str(something['from_id'])}_{str(something['id'])}"
            self.send(f"Вышел новый пост", post)
            log(False, f"[BOT_{self._CHAT_ID}] Notified about new post")

    def get_message(self, message, user_id):
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
                        self.send("Напоминание установлено")
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
                    respond['text'] = self.game(message[1])
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
                        if len(users[self._CHAT_ID]['tasks']) == 0:
                            respond["text"] = "У вас не установлено ни одно напоминание"
                        else:
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

            if respond['text'] or respond['attachment']:
                self.send(respond['text'], respond['attachment'])

    def debug(self, arg=None):
        if arg == "log":
            if self._OWNER:
                with open("bot.log", 'r') as f:
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
        else:
            up_time = time.time() - debug_array['start_time']
            time_d = int(up_time) / (3600 * 24)
            time_h = int(up_time) / 3600 - int(time_d) * 24
            time_min = int(up_time) / 60 - int(time_h) * 60 - int(time_d) * 24 * 60
            time_sec = int(up_time) - int(time_min) * 60 - int(time_h) * 3600 - int(time_d) * 24 * 60 * 60
            str_up_time = '%01d:%02d:%02d:%02d' % (time_d, time_h, time_min, time_sec)
            datetime_time = datetime.datetime.fromtimestamp(debug_array['start_time'])
            answer = "UPTIME: " + str_up_time + "<br>Прослушано сообщений: " + str(
                debug_array['messages_get']) + " (Отправлено " + str(
                debug_array['messages_answered']) + ")<br>Ошибок в работе: " + str(
                debug_array['logger_warnings']) + " (Из них беды с ВК: " + str(debug_array['vk_warnings']) + ")<br>Обьектов бота: " + str(len(bot)) + "<br>Запуск бота по часам сервера: " + datetime_time.strftime('%d.%m.%Y %H:%M:%S UTC')
            return answer

    def reminder(self, string, stage):
        if stage == "task":
            self._SET_UP_REMINDER['task'] = string
            return True
        elif stage == "time":
            try:
                datetime_object = time.strptime(string, '%d.%m.%y %H:%M')
                self._SET_UP_REMINDER['time'] = int(time.mktime(datetime_object))
                try:
                    users[self._CHAT_ID]['tasks'][self._SET_UP_REMINDER['time']] = self._SET_UP_REMINDER['task']
                except KeyError:
                    users[self._CHAT_ID].setdefault("tasks", {})
                    users[self._CHAT_ID]['tasks'][self._SET_UP_REMINDER['time']] = self._SET_UP_REMINDER['task']
                update_users_json(users)
                log(False, f"[BOT_{self._CHAT_ID}] New reminder set")
                return True
            except ValueError:
                return False
        elif stage == "remind":
            self.send(f"Пришло время вам напомнить: {string}")
            log(False, f"[BOT_{self._CHAT_ID}] Reminder worked")
            return True
        elif stage == "list":
            if len(users[self._CHAT_ID]['tasks']) == 0:
                respond = "У вас не установлено ни одно напоминание"
            else:
                respond = 'Установленные напоминания:<br>'
                for i in users[self._CHAT_ID]['tasks']:
                    datetime_time = datetime.datetime.fromtimestamp(int(i))
                    respond += f"<br>{datetime_time.strftime('%d.%m.%y %H:%M')} - {users[self._CHAT_ID]['tasks'][i]}"
            return respond
        elif stage == "delete":
            for i in users[self._CHAT_ID]['tasks']:
                    if users[self._CHAT_ID]['tasks'][i] == string:
                        users[self._CHAT_ID]['tasks'].pop(i)
                        return True
            return False

    def game(self, thing):
        if thing == "статистика":
            with open("data_file.json", "r") as read_file:
                data = json.load(read_file)
                if str(self._CHAT_ID) in data:
                    winrate = (data[str(self._CHAT_ID)]['wins'] / data[str(self._CHAT_ID)]['games']) * 100
                    return f"Камень, ножницы, бумага<br>Сыграно игр: {data[str(self._CHAT_ID)]['games']}<br>Из них:<br>•Побед: {data[str(self._CHAT_ID)]['wins']}<br>•Поражений: {data[str(self._CHAT_ID)]['defeats']}<br>•Ничей: {data[str(self._CHAT_ID)]['draws']}<br>Процент побед: {toFixed(winrate, 2)}%"
                else:
                    return "Похоже, вы ещё никогда не играли в Камень, ножницы, бумага"
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
            elif result == 1:
                response = f"Камень, ножницы, бумага<br>{thing} vs. {bot_thing}<br>Вы проиграли!"
            elif result == 0:
                response = f"Камень, ножницы, бумага<br>{thing} vs. {bot_thing}<br>Ничья!"

            with open("data_file.json", 'r') as write_file:
                try:
                    data = json.load(write_file)
                except Exception:
                    data = {}
                if str(self._CHAT_ID) not in data:
                    data[str(self._CHAT_ID)] = {}
                    data[str(self._CHAT_ID)]["games"] = 0
                    data[str(self._CHAT_ID)]["wins"] = 0
                    data[str(self._CHAT_ID)]["defeats"] = 0
                    data[str(self._CHAT_ID)]["draws"] = 0

                if result == 2:
                    data[str(self._CHAT_ID)]["games"] += 1
                    data[str(self._CHAT_ID)]["wins"] += 1
                elif result == 1:
                    data[str(self._CHAT_ID)]["games"] += 1
                    data[str(self._CHAT_ID)]["defeats"] += 1
                elif result == 0:
                    data[str(self._CHAT_ID)]["games"] += 1
                    data[str(self._CHAT_ID)]["draws"] += 1

                with open("data_file.json", "w") as write_file:
                    json.dump(data, write_file)
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

    def change_await(self, awaiting=None):
        self._AWAITING_INPUT_MODE = awaiting
        try:
            users[self._CHAT_ID]['await']= self._AWAITING_INPUT_MODE
        except KeyError:
            users[self._CHAT_ID].setdefault("tasks", None)
            users[self._CHAT_ID]['await']= self._AWAITING_INPUT_MODE
        update_users_json(users)
    
    def change_access(self, level):
        self._ACCESS_LEVEL = level
        try:
            users[self._CHAT_ID]['access']= self._ACCESS_LEVEL
        except KeyError:
            users[self._CHAT_ID].setdefault("tasks", None)
            users[self._CHAT_ID]['access']= self._ACCESS_LEVEL
        update_users_json(users)

    def change_new_post(self, new_post):
        self._NEW_POST = new_post
        try:
            users[self._CHAT_ID]['new_post']= self._NEW_POST
        except KeyError:
            users[self._CHAT_ID].setdefault("new_post", None)
            users[self._CHAT_ID]['new_post']= self._NEW_POST
        update_users_json(users)
    
    def change_midnight(self, midnight):
        self._MIDNIGHT_EVENT = midnight
        try:
            users[self._CHAT_ID]['midnight']= self._MIDNIGHT_EVENT
        except KeyError:
            users[self._CHAT_ID].setdefault("midnight", None)
            users[self._CHAT_ID]['midnight']= self._MIDNIGHT_EVENT
        update_users_json(users)

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
                    bot[event.message.peer_id].get_message(event.message.text, event.message.from_id)
                else:
                    bot[event.message.peer_id] = VkBot(event.message.peer_id)
                    users[event.message.peer_id] = {"midnight": False, "tasks": {}, "await": None, "access": 1, "new_post": False}
                    update_users_json(users)
                    bot[event.message.peer_id].get_message(event.message.text, event.message.from_id)
            elif event.type == VkBotEventType.WALL_POST_NEW:
                log(False, f"[NEW_POST] id{event.object.id}")
                for i in users:
                    bot[int(i)].event("post", event.object)
            else:
                log(False, str(event))
        except Exception as kek:
            err = "Беды с ботом: " + str(kek)
            log(True, err)
            continue

def midnight():
    while True:
        current_time = time.time()+10800
        if int(current_time) % 86400 == 0:
            log(False, "[EVENT_STARTED] \"Midnight\"")
            for i in users:
                bot[int(i)].event("midnight")
            log(False, "[EVENT_ENDED] \"Midnight\"")
            time.sleep(1)
        else:
            time.sleep(0.50)

def check_tasks():
    while True:
        try:
            for i in users:
                current_time = time.time()+10800
                if "tasks" in users[i]:
                    try:
                        for n in users[i]["tasks"]:
                            if int(n) == int(current_time):
                                bot[int(i)].reminder(users[i]['tasks'][n], "remind")
                                users[i]['tasks'].pop(n)
                                update_users_json(users)
                    except RuntimeError:
                        continue
        except RuntimeError:
            continue
        time.sleep(0.3)           


log(False, "Script started, reading users.json")
load_users()
tread_bots = threading.Thread(target=bots)
tread_midnight = threading.Thread(target=midnight, daemon=True)
tread_tasks = threading.Thread(target=check_tasks, daemon=True)
tread_bots.start()
tread_midnight.start()
tread_tasks.start()


