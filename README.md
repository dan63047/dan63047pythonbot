# Мой личный бот на python для ВК
#### от dan63047
 
Для того, что бы бот работал, нужно сначала создать в папкпе бота файл `config.py`, который должен иметь следующее содержание:
    `import vk_api
    token = "*токен вашего сообщества*"
    vk = vk_api.VkApi(token=token)`