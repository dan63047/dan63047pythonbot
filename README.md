# Мой личный бот на python для ВК
#### от dan63047
Этот бот просто отвечает на поддержваемые запросы в переписке с сообществом. Был написан мною в целях изучения python
# Функции бота
Чтобы воспользоваться функциями бота необходимо отправить команду и в некоторых случаях агрумент. Все команды начинаются с восклицательного знака

* **!h, !help** — бот отправляет список команд и их краткое описание, а так же дату последнего обновления и ссылку на этот репозиторий
* **!my_id** — бот достаёт из вашего сообщения `user_id` и отправляет его вам
* **!user_id *id*** — бот отправляет *id* нужного вам пользователя в vk api методом `users.get` и отправляет вам полученные этим методом данные: имя, фамилия, id, пол, время последнего онлайна и платформы, закрыт ли профиль
* **!group_id *id*** — бот отправляет *id* нужного вам сообщества в vk api методом `groups.getById` и отправляет вам полученные этим методом данные: название, описание, id, количество подписчиков
* **!image** — бот, с помощью костыля в виде сервисного ключа приложения, получает vk api методом `photos.get` фотографии альбома, выбирает с помощью функции в python `random.randrange` одну фотографию и отправляет вам её как attachment
* **!random *число1* *число2*** — бот генерирует с помощью `random.randint()` случайное число и отправляет его вам. Если без аргументов, то число от 0 до 10. Если есть одно число, то от 0 до *число1*. Если есть оба числа, то от *число1* до *число2*
* **!weather *город*** — бот получает с помощью OpenWeather API текущую погоду в городе и отправляет её вам
* **!wiki *запрос*** — бот получает с помощью Wikipedia API краткое описание статьи по запросу и отправляет её вам
* **!byn** — бот получает с помощью НБ РБ API текущий курс белорусского рубля и отправляет её вам
* **!echo** — бот начинает повторять за вами, чтобы это остановить, надо написать *!echo off*
* **!game *камень/ножницы/бумага/статистика*** — бот играет с вами в "Камень, ножницы, бумага" и ведет статискику игр, которую записывает в файл БД
* **!midnight** — бот будет уведомлять о каждом миднайте по Московскому времени. Введите ещё раз, чтобы отменить это
* **!reminder *set/list/delete*** — напоминалка. С агрументом *set* бот запускает установку напоминания, с аргументом *list* отправляет вам все ваши запланированные напоминания, с аргументом *delete* запускает удаление напоминания
* **!subscribe** — бот будет уведомлять вас о каждом новом посте. Введите ещё раз, чтобы отменить это
* **!debug** — бот отправляет информацию о своём состоянии
* **!debug *log*** — бот отправляет последние 10 строк из своего лога. Доступно только вам
* **!debug *bots*** — бот отправляет информацию о обьектах бота в памяти. Доступно только вам
* **!debug *game*** — бот отправляет всю статистику по игре !game
* **!debug *tasks*** — бот отправляет вам все напоминания из !reminder. Доступно только вам
* **!access *all/owner*** — позволяет в беседе установить уровень доступа к командам *!midnight*, *!subscribe* и *!debug*. *all* - все могут пользоваться. *owner* - только вы. Доступно только вам
* **!turnoff** — даёт боту команду на выключение. Доступно только вам
* **!admin_mode** — если чат, в которой активируется команда, является беседой и в ней у бота есть полномочия администратора, то бот переходит в режим модерации. Пока что он может только кикать людей за @all и @online. Введите ещё раз, чтобы выключить режим модерации. Доступно только вам
# Установка и запуск бота
## Как это делал я
Здесь я расскажу каким образом я запустил этого бота. Работает он у меня на [pythonanywhere](https://www.pythonanywhere.com/), причём аккаунт платный, ибо он использует MySQL базу данных, а также работает как Always-on task. Можно, конечно, не использовать БД и запускать бота в консоли, но он будет сыпать ошибками из-за тесной связи с этой самой БД, не будет сохранять данные о своей работе, да ещё и pythonanywhere выключит вашу консоль, если вы долго не будете посещать её.

Итак, заходим на pythonanywhere, входим или регистрируемся и покупаем самый дешёвый тариф Hacker за 5 баксов в месяц, этого должно хватить.

Создаём консоль на bash и прописываем:

`git clone https://github.com/dan63047/dan63047pythonbot.git`

Эта команда создаст папку `dan63047pythonbot` и поместит туда бота.

Теперь заходим в директорию бота (`cd dan63047pythonbot/`) и устанавливаем необходимые библиотеки:

`pip3 install vk-api pyowm Wikipedia-API PyMySQL --user`

Эта команда установит все необходимые библиотеки для работы бота.

Теперь создадим базу данных, с которой бот будет работать. На том же pythonanywhere тыкаем на *Databases* в шапке сайта. Создаём пароль для вашей базы данных. По умолчанию будет создана база данных с названием `your_nickname$default`, но вы можете создать БД со своим названием.

Настроим ваше сообщество для работы с ботом: заходим в *Управление -> Работа с API*. Здесь создаём токен сообщества с правами доступа к сообщениям, фотографиям и стене. Идем в *Long Poll API*, включаем его и ставим последнюю доступную версию (на момент написания этой версии README это 5.108). В *Типы событий* должны стоять галочки на следующих событиях: Входящее сообщение, Запрет на получение, Добавление записи на стене.

Разберёмся с костылём для метода `photos.get`: Идем на `vk.com/dev`, нажимаем на *Мои приложения* и кликаем по *Создать приложение*. Новое приложение может называться как угодно, от него нам необходимо всего лишь сервисный ключ доступа, который можно найти, если нажать на *Настройки*

Если вы планируете использовать команду !weather, сделайте следующее:
Перейдите по `openweathermap.org`, пройдите там регистрацию и создайте API ключ

Создадим файл конфигурации для бота: В pythonanywhere тыкаем на *Files*, переходим в директорию *dan63047pythonbot* и создаём там новый фаил с названием `config.py`. В нём должно быть написано следующее:
```python
import vk_api
import pyowm
vk = vk_api.VkApi(token="vk_group_token") # Токен сообщества
vk_mda = vk_api.VkApi(token="vk_service_token") # Сервисный ключ доступа
group_id = 190322075 # Цифровой ид группы
album_for_command = 269199619 # Цифровой ид альбома для команды !image
owner_id = 276193568 # Цифровой ид вашей страницы вк, чтобы вы могли управлять ботом в переписке
owm = pyowm.OWM('openweathermap_api_key', language='ru') # Ключ OpenWeather API
mysql_host = 'pythonanywhere_nickname.mysql.pythonanywhere-services.com' # ссылка на хост БД. Вместо pythonanywhere_nickname должен быть ваш никнейм на pythonanywhere
mysql_user = 'pythonanywhere_nickname' # Ваш никнейм на pythonanywhere
mysql_pass = 'qwerty123' # Пароль, созданный вами для БД
mysql_db = 'pythonanywhere_nickname$default' # Название вашей БД. Вместо pythonanywhere_nickname должен быть ваш никнейм на pythonanywhere. Так же вместо default может быть ваше название БД
```
И, наконец, запуск бота: в pythonanywhere тыкаем на *Tasks*, создаём и запускаем в *Always-on tasks* задачу `python3.8 /home/pythonanywhere_nickname/dan63047pythonbot/dan63047bot.py`, где вместо pythonanywhere_nickname должен быть ваш никнейм на pythonanywhere. После небольшого тупления pythonanywhere запустит вашего бота и он будет работать долго и счастливо.
## Другие варианты запуска бота
Скорее всего, вы можете найти где-нибудь VPS с базами данных или огранизовать всё на своём компьютере, но об этом я ничего не знаю. Напишите мне, чтобы рассказать, как у вас полностью получилось заставить работать бота.
# Использованные библиотеки
* [vk_api](https://github.com/python273/vk_api) — модуль для создания скриптов для социальной сети Вконтакте
* [pyowm](https://github.com/csparpa/pyowm) — модуль для получения погоды через OpenWeather API
* [Wikipedia-API](https://github.com/martin-majlis/Wikipedia-API) — модуль для получения статей из Wikipedia
* [PyMySQL](https://github.com/PyMySQL/PyMySQL/) — Pure Python MySQL Client
# Дополнительно
С ботом можно пообщаться [здесь](https://vk.com/im?sel=-190322075)

Автор бота: [Даниил Михайлов](https://vk.com/dan63047)

Буду рад помощи и поддержке