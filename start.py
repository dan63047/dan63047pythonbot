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

class MyVkLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try: 
                for event in self.check():
                    yield event
            except Exception as e:
                logging.warning("Беды с ВК: "+str(e))
                continue

async def main():
    for event in MyVkLongPoll.listen(longpoll):
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                logging.info(f'Новое сообщение в чате id{event.message.peer_id}: {event.message.text}')
                bot = VkBot(event.message.peer_id, event.message.from_id)
                await bot.new_message(event.message.text)
        except Exception as kek:
            logging.warning("Беды с ботом: "+str(kek))
            continue   

logging.info("Бот начал работу")

asyncio.run(main())

    