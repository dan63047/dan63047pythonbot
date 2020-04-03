import vk_api, time, bs4
from dan63047bot import VkBot
from vk_api.longpoll import VkLongPoll, VkEventType 

def write_msg(peer_id, message):
    vk.method('messages.send', {'peer_id': peer_id, 'message': message, 'random_id': time.time()})

token = "9c2e8fbc0fb7c846315e2f7758373d92e6961cefe74697ffb335e14a67916e54e20df6082577c8a7ade1c"# API-ключ созданный ранее
vk = vk_api.VkApi(token=token)# Авторизуемся как сообщество
longpoll = VkLongPoll(vk)# Работа с сообщениями
print("Server started")
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:
        
            print('New message:')
            print(f'For me by: {event.peer_id}', end='')
            
            bot = VkBot(event.peer_id)
            write_msg(event.peer_id, bot.new_message(event.text))
            
            print('Text: ', event.text)