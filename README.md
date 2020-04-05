# Мой личный бот на python для ВК
#### от dan63047

Этот бот просто отвечает на поддержваемые запросы в переписке с сообществом
 
Для того, что бы бот работал, сначала нужно создать в папке бота файл `config.py`, который должен иметь следующее содержание:

```python
import vk_api
import pyowm
vk = vk_api.VkApi(token="vk_group_access_token") # Токен сообщества в ВК
vk_mda = vk_api.VkApi(token="vk_app_service_key") # Костыль для того, чтобы работал метод photos.get
own = pyowm.OWM('OpenWeather_api_key', language='ru') # Ключ OpenWeather API для функции погоды
```

Запустите `start.py`, что бы бот начал слушать сервер
