import vk_api
import datetime
import requests
import logging
import pyowm
from config import vk, owm
from bs4 import BeautifulSoup
from vk_api.longpoll import VkLongPoll, VkEventType

bot_logger = logging.getLogger("dan63047bot")

class VkBot:

    def __init__(self, peer_id, user_id):

        bot_logger.info("Создан объект бота!")
        self._USER_ID = user_id
        self._CHAT_ID = peer_id

        self._COMMANDS = ["!image", "!my_id", "!h", "!user_id", "!group_id", "!help", "!weather"]

    @staticmethod
    def _clean_all_tag_from_str(string_line):
        result = ""
        not_skip = True
        for i in list(string_line):
            if not_skip:
                if i == "<":
                    not_skip = False
                else:
                    result += i
            else:
                if i == ">":
                    not_skip = True
        return result

    def get_weather(self, place):
        logger = logging.getLogger("dan63047bot.get_weather")
        try:
            weather_request = owm.weather_at_place(place)
        except pyowm.exceptions.api_response_error.NotFoundError as i:
            logger.warning("Ошибка OpenWeather API: "+str(i))
            return "Такого города нет, либо данных о погоде нет"
        weather_answer = weather_request.get_weather()
        logger.info("Результат поиска погоды через OpenWeather API: "+str(weather_answer))
        return "В городе "+place+" сейчас "+weather_answer.get_detailed_status()+", "+str(round(weather_answer.get_temperature('celsius')['temp']))+"°C"

    def get_info_user(self, id):
        logger = logging.getLogger("dan63047bot.get_info_user")
        try:
            user_info = vk.method('users.get', {'user_ids': id, 'fields': 'verified,last_seen,sex'})
        except vk_api.exceptions.ApiError as lol:
            logger.warning("Ошибка метода users.get: "+str(lol))
            return "Пользователь не найден<br>"+str(lol)
        
        logger.info("Результат метода API users.get: "+str(user_info))
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

        answer = user_info[0]['first_name']+" "+user_info[0]['last_name']+"<br>Его ид: "+str(user_info[0]['id'])+"<br>Профиль закрыт: "+is_closed+"<br>Пол: "+sex+"<br>Последний онлайн: "+time.strftime('%d.%m.%Y в %H:%M:%S')+" ("+platform+")"

        return answer

    def get_info_group(self, id):
        logger = logging.getLogger("dan63047bot.get_info_group")
        try:
            group_info = vk.method('groups.getById', {'group_id': id, 'fields': 'description,members_count'})
        except vk_api.exceptions.ApiError as lol:
            logger.warning("Ошибка метода groups.getById: "+str(lol))
            return "Группа не найдена<br>"+str(lol)
        
        logger.info("Результат метода API groups.getById: "+str(group_info))
        if group_info[0]['description'] == "":
            description = "Отсутствует"
        else:
            description = group_info[0]['description']

        answer = group_info[0]['name']+"<br>Описание: "+description+"<br>Ид группы: "+str(group_info[0]['id'])+"<br>Подписчиков: "+str(group_info[0]['members_count'])
        return answer

    def new_message(self, message):
        respond = {'attachment': None, 'text': None}
        message = message.split(' ')
        if message[0] == self._COMMANDS[0]:
            respond['text'] = "hueh"
            respond['attachment'] = "photo-190322075_457239033" 

        elif message[0] == self._COMMANDS[1]:
            respond['text'] = "Ваш ид: "+str(self._USER_ID)

        elif message[0] == self._COMMANDS[2] or message[0] == self._COMMANDS[5]:
            respond['text'] = "Я бот, призванный доставлять неудобства. <br>Команды:<br>!my_id - сообщит ваш id в ВК<br>!user_id *id* - сообщит информацию о этом пользователе<br>!group_id *id* - сообщит информацию о этой группе<br>!image - отправляет пока что только одну картинку (скоро планируется отправлять рандомную картинку из альбома)<br>!weather *город* - отправляет текущую погоду в городе(данные из OpenWeather API)<br>!h, !help - справка<br>Дата последнего обновления: 05.04.2020<br>Проект бота на GitHub: https://github.com/dan63047/dan63047pythonbot"

        elif message[0] == self._COMMANDS[3]:
            try:
                respond['text'] = self.get_info_user(message[1])
            except IndexError:
                respond['text'] = "Отсуствует аргумент"
        
        elif message[0] == self._COMMANDS[4]:
            try:
                respond['text'] = respond['text'] = self.get_info_group(message[1])
            except IndexError:
                respond['text'] = "Отсуствует аргумент"

        elif message[0] == self._COMMANDS[6]:
            try:
                respond['text'] = respond['text'] = self.get_weather(message[1])
            except IndexError:
                respond['text'] = "Отсуствует аргумент"
            except AttributeError as lol:
                respond['text'] = "Пайтон в ахуе: "+str(lol)

        return respond
