import vk_api
import time
import logging
import requests
import asyncio
from config import vk, group_id
from dan63047bot import VkBot
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

root_logger= logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.FileHandler('bot.log', 'w', 'utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)

longpoll = VkBotLongPoll(vk, group_id)

def listening():
    while True:
        try:
            event = longpoll.listen()
            return event
        except Exception as mda:
            logging.warning("Беды с ВК: "+str(mda))
            continue

async def main():
    for event in listening():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                logging.info(f'Новое сообщение в чате id{event.message.peer_id}: {event.message.text}')
                bot = VkBot(event.message.peer_id, event.message.from_id)
                result = await bot.new_message(event.message.text)
                message = vk.method('messages.send', {'peer_id': event.message.peer_id, 'message': result['text'], 'random_id': time.time(), 'attachment': result['attachment']})
                logging.info(f'Ответ бота: {result}')
                logging.info(f'Отправлено методом messages.send: {message}')
        except Exception as kek:
            logging.warning("Беды с ботом: "+str(kek))
            continue   

logging.info("Бот начал работу")

asyncio.run(main())

    