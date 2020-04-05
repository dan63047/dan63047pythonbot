import vk_api
import time
import requests
import logging
from config import vk
from bs4 import BeautifulSoup
from dan63047bot import VkBot
from vk_api.longpoll import VkLongPoll, VkEventType

root_logger= logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler('bot.log', 'w', 'utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)

def write_msg(peer_id, message, attachment=None):
    vk.method('messages.send', {'peer_id': peer_id,
                                'message': message,
                                'random_id': time.time(),
                                'attachment': attachment})

longpoll = VkLongPoll(vk)  # Работа с сообщениями
logging.info("Бот начал работу")
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:

            logging.info(f'Получено сообщение от id{event.peer_id}: {event.text}')

            bot = VkBot(event.peer_id)
            bot_answer = bot.new_message(event.text)
            if bot_answer['text'] or bot_answer['attachment']:
                write_msg(event.peer_id, bot_answer['text'], bot_answer['attachment'])
            
            logging.info(f'Ответ бота: {bot_answer}')