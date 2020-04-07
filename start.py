import vk_api
import time
import logging
from config import vk, group_id
from dan63047bot import VkBot
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

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

longpoll = VkBotLongPoll(vk, group_id)  # Работа с сообщениями
logging.info("Бот начал работу")
for event in longpoll.listen():
    try:
        if event.type == VkBotEventType.MESSAGE_NEW:

            logging.info(f'Новое сообщение в чате id{event.message.peer_id}: {event.message.text}')

            bot = VkBot(event.message.peer_id, event.message.from_id)
            bot_answer = bot.new_message(event.message.text)
            if bot_answer['text'] or bot_answer['attachment']:
                write_msg(event.message.peer_id, bot_answer['text'], bot_answer['attachment'])
            
            logging.info(f'Ответ бота: {bot_answer}')
    except Exception as kek:
        logging.warning("Беды с ботом: "+str(kek))
        continue