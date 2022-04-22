import vk_api
import datetime
import time
import logging
import random
import json
import threading
import config
import dan63047VKbot
from pymysql.cursors import DictCursor
from collections import deque
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
try:
    log_path = f'logs/console_log{str(datetime.datetime.now())}.log'
    handler = logging.FileHandler(log_path, 'w', 'utf-8')
except:
    log_path = 'console.log'
    handler = logging.FileHandler(log_path, 'w', 'utf-8')
handler.setFormatter(logging.Formatter('%(message)s'))
root_logger.addHandler(handler)

def log(warning, text):
    if warning:
        msg = "[" + str(datetime.datetime.now()) + "] [WARNING] " + text
        logging.warning(msg)
        print(msg)
    else:
        msg = "[" + str(datetime.datetime.now()) + "] " + text
        logging.info(msg)
        print(msg)

try:
    vk = vk_api.VkApi(token=config.vk_group_token)
    longpoll = VkBotLongPoll(vk, config.group_id)
    log(False, "VK API Group token: OK")
except Exception as e:
    log(True, "Can't connect to longpull: "+str(e))
    exit(log(False, "[SHUTDOWN]"))


def cycle():
    active = True
    dan63047VKbot.load_users()
    print("Welcome to dan63047bot console\nEnter command:")
    while active:
        command = input(">")
        logging.info("[" + str(datetime.datetime.now()) + "] Entered command: " + command)
        command = command.split(' ', 1)
        if command[0] == "exit":
            print("Bye")
            active = False
        elif command[0] == "help":
            print("Console in development")
            print("help - command list")
            print("exit - shutdown console")
            print("message [peer_id] [message] - send message in vk from bot to peer_id")
            print("msg_history [peer_id] [count] - return message history in 'count' last messages with peer_id")
        elif command[0] == "message":
            try:
                command[1] = command[1].split(' ', 1)
            except:
                log(True, "No arguments")
                continue
            random_id = random.randint(-9223372036854775808, 9223372036854775807)
            try:
                m = vk.method('messages.send', {'peer_id': command[1][0], 'message': command[1][1], 'random_id': random_id})
                log(False, f'message_id: {m}, peer_id: {command[1][0]}, random_id: {random_id}')
            except Exception as e:
                log(True, f'Failed to send message: {str(e)}')
        elif command[0] == "msg_history":
            try:
                command[1] = command[1].split(' ', 1)
            except:
                log(True, "No arguments")
                continue
            try:
                if len(command[1]) == 2:
                    m = vk.method('messages.getHistory', {'count': command[1][1], 'peer_id': command[1][0]})
                else:
                    m = vk.method('messages.getHistory', {'peer_id': command[1][0]})
                log(False, f"That dialogue have {m['count']} messages ({len(m['items'])} in response)")
                for i in m['items']:
                    if str(i['from_id']) == "-"+str(config.group_id):
                        f = "You"
                    else:
                        user_info = vk.method('users.get', {'user_ids': i["from_id"], 'fields': 'verified,last_seen,sex'})
                        f = f'{user_info[0]["first_name"]} {user_info[0]["last_name"]}'
                    datetime_time = datetime.datetime.fromtimestamp(i['date'])
                    date = datetime_time.strftime('%d.%m.%Y %H:%M:%S')
                    msg = f"{f} {date}: {i['text']}"
                    if i['attachments']:
                        for m in i['attachments']:
                            if m['type'] == "sticker":
                                msg += f" [sticker_id{m[m['type']]['sticker_id']}]"
                            elif m['type'] == "wall":
                                msg += " [" + m['type'] + str(m[m['type']]['from_id']) + \
                                    "_" + str(i[m['type']]['id']) + "]"
                            elif m['type'] == "link":
                                msg += " [" + m['type'] + " " + m[m['type']]['title'] + "]"
                            else:
                                msg += " [" + m['type'] + str(m[m['type']]['owner_id']) + \
                                    "_" + str(m[m['type']]['id']) + "]"
                    print(msg)
            except Exception as e:
                log(True, f'Failed to get history: {str(e)}')
        elif command[0] == "bot":
            if len(command) == 2:
                command[1] = command[1].split(' ', 1)
                if len(command[1]) == 2:
                    if command[1][0] == "midnight":
                        try:
                            userinfo = dan63047VKbot.db.get_from_users(command[1][1])
                            log(False, "Midnight flag: "+str(userinfo["midnight"]))
                            dan63047VKbot.bot[int(command[1][1])].event("midnight")
                        except KeyError as e:
                            log(True, "Bot object is not exist: "+str(e))
                    elif command[1][0] == "changeMidnightFlag":
                        try:
                            userinfo = dan63047VKbot.db.get_from_users(command[1][1])
                            if userinfo["midnight"]:
                                dan63047VKbot.bot[int(command[1][1])].change_flag('midnight', False)
                            else:
                                dan63047VKbot.bot[int(command[1][1])].change_flag('midnight', True)
                            userinfo = dan63047VKbot.db.get_from_users(command[1][1])
                            log(False, "Midnight flag: "+str(userinfo["midnight"]))
                        except KeyError as e:
                            log(True, "Bot object is not exist: "+str(e))
                    elif command[1][0] == "create":
                        try:
                            dan63047VKbot.bot[user_id] = dan63047VKbot.VkBot(command[1][1])
                            log(False, "Bot-object has been created")
                        except Exception as e:
                            log(True, "Can't create bot-object - "+str(e))
                    elif command[1][0] == "delete":
                        try:
                            del dan63047VKbot.bot[int(command[1][1])]
                            dan63047VKbot.db.delete_user(command[1][1])
                            log(False, "Bot-object has been deleted")
                        except Exception as e:
                            log(True, "Can't delete bot-object - "+str(e))
                else:
                    if command[1][0] == "update":
                        dan63047VKbot.load_users()
            else:
                if dan63047VKbot.bot:
                    log(False, f"There is {len(dan63047VKbot.bot)} bot-objects")
                    for i in dan63047VKbot.bot:
                        print(dan63047VKbot.bot[i])
                else:
                    print("No bot-objects")
        else:
            log(True, "Unknown command. Type 'help' for command list")

cycle()
