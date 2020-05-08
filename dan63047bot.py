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
from config import vk, owm, vk_mda, group_id, album_for_command, owner_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

bot = {}
users = []
debug_array = {'vk_warnings': 0, 'logger_warnings': 0, 'start_time': 0, 'messages_get': 0, 'messages_answered': 0}

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler('bot.log', 'w', 'utf-8')
handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
root_logger.addHandler(handler)

longpoll = VkBotLongPoll(vk, group_id)


def log(warning, text):
    if warning:
        logging.warning(text)
        debug_array['logger_warnings'] += 1
        print("[" + time.strftime("%d.%m.%Y %H:%M:%S", time.gmtime()) + "][WARNING] " + text)
    else:
        logging.info(text)
        print("[" + time.strftime("%d.%m.%Y %H:%M:%S", time.gmtime()) + "] " + text)


def toFixed(numObj, digits=0):
    return f"{numObj:.{digits}f}"


class MyVkLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except Exception as e:
                err = "Беды с ВК: " + str(e)
                log(True, err)
                debug_array['vk_warnings'] += 1
                time.sleep(15)
                continue


def get_weather(place):
    try:
        weather_request = owm.weather_at_place(place)
    except pyowm.exceptions.api_response_error.NotFoundError as i:
        err = "Ошибка OpenWeather API: " + str(i)
        log(True, err)
        return "Такого города нет, либо данных о погоде нет"
    weather_answer = weather_request.get_weather()
    info = "Результат поиска погоды через OpenWeather API: " + str(weather_answer)
    log(False, info)
    return "В городе " + place + " сейчас " + weather_answer.get_detailed_status() + ", " + str(
        round(weather_answer.get_temperature('celsius')['temp'])) + "°C"


class VkBot:

    def __init__(self, peer_id, user_id):

        log(False, f"Создан объект бота! id{peer_id}")
        self._USER_ID = user_id
        self._CHAT_ID = peer_id
        self._MIDNIGHT_EVENT = False
        self._ECHO_MODE = False

        if self._USER_ID == owner_id and self._CHAT_ID <= 2000000000:
            self._OWNER = True
        else:
            self._OWNER = False

        self._COMMANDS = ["!image", "!my_id", "!h", "!user_id", "!group_id", "!help", "!weather", "!wiki", "!byn",
                          "!echo", "!game", "!debug", "!midnight"]

    def event(self, event):
        if event == "midnight" and self._MIDNIGHT_EVENT:
            self.send("Миднайт")
            log(False, f"Бот id{self._CHAT_ID} оповестил о миднайте")

    def get_message(self, message):
        if self._ECHO_MODE:
            if message == "!echo off":
                self.send(message)
                self._ECHO_MODE = False
                log(False, f"Бот id{self._CHAT_ID} вышел из режима эхо")
                debug_array['messages_answered'] += 1
            else:
                self.send(message)
                log(False, f"Эхо-бот id{self._CHAT_ID}: {message}")
                debug_array['messages_answered'] += 1
        else:
            respond = {'attachment': None, 'text': None}
            message = message.split(' ', 1)
            if message[0] == self._COMMANDS[0]:
                respond['attachment'] = self.random_image()

            elif message[0] == self._COMMANDS[1]:
                respond['text'] = "Ваш ид: " + str(self._USER_ID)

            elif message[0] == self._COMMANDS[2] or message[0] == self._COMMANDS[5]:
                respond[
                    'text'] = "Я бот, призванный доставлять неудобства. <br>Команды:<br>!my_id - сообщит ваш id в ВК<br>!user_id *id* - сообщит информацию о этом пользователе<br>!group_id *id* - сообщит информацию о этой группе<br>!image - отправляет рандомную картинку из альбома<br>!weather *город* - отправляет текущую погоду в городе (данные из OpenWeather API)<br>!wiki *запрос* - отправляет информацию об этом из Wikipedia<br>!byn - отправляет текущий курс валют, полученный из API НБ РБ<br>!echo - бот отправляет вам всё, что вы ему пишите<br>!game *камень/ножницы/бумага/статистика* - бот будет играть с вами в \"Камень, ножницы, бумага\" и записывать статистику<br>!midnight - бот будет уведомлять вас о 00:00 по Москве. Отправьте ещё раз, чтобы бот больше вас не уведомлял<br>!h, !help - справка<br>Дата последнего обновления: 08.05.2020 (!midnight и перестройка бота)<br>Проект бота на GitHub: https://github.com/dan63047/dan63047pythonbot"

            elif message[0] == self._COMMANDS[3]:
                try:
                    respond['text'] = self.get_info_user(message[1])
                except IndexError:
                    respond['text'] = "Отсуствует аргумент"

            elif message[0] == self._COMMANDS[4]:
                try:
                    respond['text'] = self.get_info_group(message[1])
                except IndexError:
                    respond['text'] = "Отсуствует аргумент"

            elif message[0] == self._COMMANDS[6]:
                try:
                    respond['text'] = get_weather(message[1])
                except IndexError:
                    respond['text'] = "Отсуствует аргумент"

            elif message[0] == self._COMMANDS[7]:
                try:
                    respond['text'] = self.wiki_article(message[1])
                except IndexError:
                    respond['text'] = "Отсуствует аргумент"

            elif message[0] == self._COMMANDS[8]:
                respond['text'] = self.exchange_rates()

            elif message[0] == self._COMMANDS[9]:
                vk.method('messages.send', {'peer_id': self._CHAT_ID,
                                            'message': "Теперь бот работает в режиме эхо. Чтобы"
                                                       " это выключить, введить \"!echo off\"",
                                            'random_id': time.time()})
                self._ECHO_MODE = True
                log(False, f"Бот id{self._CHAT_ID} в режиме эхо")

            elif message[0] == self._COMMANDS[10]:
                try:
                    message[1] = message[1].lower()
                    respond['text'] = self.game(message[1])
                except IndexError:
                    respond['text'] = "Отсуствует аргумент"

            elif message[0] == self._COMMANDS[11]:
                try:
                    respond['text'] = self.debug(message[1])
                except IndexError:
                    respond['text'] = self.debug()

            elif message[0] == self._COMMANDS[12]:
                if self._MIDNIGHT_EVENT:
                    self._MIDNIGHT_EVENT = False
                    self.send("Уведомление о миднайте выключено")
                    log(False, f"Бот id{self._CHAT_ID}: Юзер отписался от ивента \"Миднайт\"")
                else:
                    self._MIDNIGHT_EVENT = True
                    self.send("Бот будет уведомлять вас о каждом миднайте")
                    log(False, f"Бот id{self._CHAT_ID}: Юзер подписался на ивент \"Миднайт\"")

            if respond['text'] or respond['attachment']:
                self.send(respond['text'], respond['attachment'])
                debug_array['messages_answered'] += 1

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
                return "Отказано в доступе"
        else:
            up_time = time.time() - debug_array['start_time']
            time_d = int(up_time) / (3600 * 24)
            time_h = int(up_time) / 3600 - int(time_d) * 24
            time_min = int(up_time) / 60 - int(time_h) * 60 - int(time_d) * 24 * 60
            time_sec = int(up_time) - int(time_min) * 60 - int(time_h) * 3600 - int(time_d) * 24 * 60 * 60
            str_up_time = '%01d:%02d:%02d:%02d' % (time_d, time_h, time_min, time_sec)
            datetime_time = datetime.datetime.fromtimestamp(debug_array['start_time'])
            answer = "UPTIME: " + str_up_time + "<br>Прослушано сообщений: " + str(
                debug_array['messages_get']) + " (Отвечено на " + str(
                debug_array['messages_answered']) + ")<br>Ошибок в работе: " + str(
                debug_array['logger_warnings']) + " (Из них беды с ВК: " + str(debug_array['vk_warnings']) + ")<br>Обьектов бота: " + str(len(bot)) + "<br>Запуск бота по часам сервера: " + datetime_time.strftime('%d.%m.%Y %H:%M:%S UTC')
            return answer

    def game(self, thing):
        if thing == "статистика":
            with open("data_file.json", "r") as read_file:
                data = json.load(read_file)
                if str(self._USER_ID) in data:
                    winrate = (data[str(self._USER_ID)]['wins'] / data[str(self._USER_ID)]['games']) * 100
                    return f"Камень, ножницы, бумага<br>Сыграно игр: {data[str(self._USER_ID)]['games']}<br>Из них:<br>•Побед: {data[str(self._USER_ID)]['wins']}<br>•Поражений: {data[str(self._USER_ID)]['defeats']}<br>•Ничей: {data[str(self._USER_ID)]['draws']}<br>Процент побед: {toFixed(winrate, 2)}%"
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
                if str(self._USER_ID) not in data:
                    data[str(self._USER_ID)] = {}
                    data[str(self._USER_ID)]["games"] = 0
                    data[str(self._USER_ID)]["wins"] = 0
                    data[str(self._USER_ID)]["defeats"] = 0
                    data[str(self._USER_ID)]["draws"] = 0

                if result == 2:
                    data[str(self._USER_ID)]["games"] += 1
                    data[str(self._USER_ID)]["wins"] += 1
                elif result == 1:
                    data[str(self._USER_ID)]["games"] += 1
                    data[str(self._USER_ID)]["defeats"] += 1
                elif result == 0:
                    data[str(self._USER_ID)]["games"] += 1
                    data[str(self._USER_ID)]["draws"] += 1

                with open("data_file.json", "w") as write_file:
                    json.dump(data, write_file)
                return response
        else:
            return "Неверный аргумент<br>Использование команды:<br>!game *камень/ножницы/бумага/статистика*"

    def get_info_user(self, id):
        try:
            user_info = vk.method('users.get', {'user_ids': id, 'fields': 'verified,last_seen,sex'})
        except vk_api.exceptions.ApiError as lol:
            err = "Ошибка метода users.get: " + str(lol)
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
            err = "Ошибка метода groups.getById: " + str(lol)
            log(True, err)
            return "Группа не найдена<br>" + str(lol)

        info = "Результат метода API groups.getById: " + str(group_info)
        log(False, info)
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
        info = "Результат метода photos.get: Получено " + str(random_images_query['count']) + " фото"
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
            err = "Ошибка получения данных из НБ РБ API: " + str(mda)
            log(True, err)
            return "Невозможно получить данные из НБ РБ: " + str(mda)

    def send(self, message=None, attachment=None):
        message = vk.method('messages.send',
                            {'peer_id': self._CHAT_ID, 'message': message, 'random_id': time.time(),
                             'attachment': attachment})
        log(False, f'Бот id{self._CHAT_ID}: Ответ метода ВК "messages.send": {message}')

def bots():
    for event in MyVkLongPoll.listen(longpoll):
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                log(False, f'Новое сообщение: {event.message}')
                debug_array['messages_get'] += 1
                if event.message.peer_id in bot:
                    bot[event.message.peer_id].get_message(event.message.text)
                else:
                    bot[event.message.peer_id] = VkBot(event.message.peer_id, event.message.from_id)
                    users.append(event.message.peer_id)
                    bot[event.message.peer_id].get_message(event.message.text)
        except Exception as kek:
            err = "Беды с ботом: " + str(kek)
            log(True, err)
            continue


def midnight():
    while True:
        if time.time()+10800 % 86400 == 0:
            for i in users:
                log(False, "Иницаилизация ивента \"Миднайт\"")
                bot[i].event("midnight")


tread_bots = threading.Thread(target=bots)
tread_midnight = threading.Thread(target=midnight)
tread_bots.start()
log(False, "Бот начал работу")
debug_array['start_time'] = time.time()
tread_midnight.start()


