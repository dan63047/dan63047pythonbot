import vk_api, time, bs4
from vk_api.longpoll import VkLongPoll, VkEventType
class VkBot:

    def __init__(self, peer_id):
    
        print("\nСоздан объект бота!")
        self._USER_ID = peer_id
        #self._USERNAME = self._get_user_name_from_vk_id(user_id)
        
        self._COMMANDS = ["привет", "!my_id", "!h", "пока"]

    def _get_user_name_from_vk_id(self, user_id):
        request = requests.get("https://vk.com/id"+str(user_id))
        bs = bs4.BeautifulSoup(request.text, "html.parser")
        
        user_name = self._clean_all_tag_from_str(bs.findAll("title")[0])
        
        return user_name.split()[0]

    def new_message(self, message):

        # Привет
        if message == self._COMMANDS[0]:
            return f"Привет-привет!"

        elif message == self._COMMANDS[1]:
            return f"Ваш ид: {self._USER_ID}"

        elif message == self._COMMANDS[2]:
            return f"Я бот, призванный доставлять неудобства. <br>Команды:<br>!my_id - сообщит ваш id в ВК<br>!user_id *id* - сообщит информацию о этом пользователе<br>!group_id *id* - сообщит информацию о этой группе<br>!image - отправляет пока что только одну картинку (скоро планируется отправлять рандомную картинку из альбома)<br>!h, !help - справка<br>Дата последнего обновления: 08.03.2020"
        
        # Пока
        elif message == self._COMMANDS[3]:
            return f"Пока-пока!"
        
        else:
            return "Не понимаю о чем вы..."
