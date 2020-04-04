import vk_api
import time
import requests
from config import vk
from bs4 import BeautifulSoup
from dan63047bot import VkBot
from vk_api.longpoll import VkLongPoll, VkEventType


def write_msg(peer_id, message, attachment=None):
    vk.method('messages.send', {'peer_id': peer_id,
                                'message': message,
                                'random_id': time.time(),
                                'attachment': attachment})

longpoll = VkLongPoll(vk)  # Работа с сообщениями
print("Server started")
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:

            print('New message:')
            print(f'For me by: {event.peer_id}', end='')

            bot = VkBot(event.peer_id)
            if bot.new_message(event.text)['text']:
                write_msg(event.peer_id, bot.new_message(event.text)['text'], bot.new_message(event.text)['attachment'])

            print('Text: ', event.text)
