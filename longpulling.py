import datetime
import time
import logging
import dan63047VKbot
import config
import vk_api
import threading

dan63047VKbot.log(False, "Script started")

def bots():
    dan63047VKbot.log(False, "Started listening longpull server")
    dan63047VKbot.debug_array['start_time'] = time.time()
    for event in dan63047VKbot.MyVkLongPoll.listen(dan63047VKbot.longpoll):
        try:
            if event.type == dan63047VKbot.VkBotEventType.MESSAGE_NEW:
                log_msg = f'[MESSAGE] id: {event.message.id}, peer_id: {event.message.peer_id}, user_id: {event.message.from_id}'
                if event.message.action:
                    log_msg += (
                        ', action: '
                        + event.message.action["type"]
                        + ', user id in action: '
                        + str(event.message.action["member_id"])
                    )

                if event.message.text != "":
                    log_msg += f', text: "{event.message.text}"'
                if event.message.attachments:
                    atch = ', attachments: '
                    for i in event.message.attachments:
                        if i['type'] == "sticker":
                            atch += f"sticker_id{i[i['type']]['sticker_id']}"
                        elif i['type'] == "wall":
                            atch += i['type'] + str(i[i['type']]['from_id']) + \
                                "_" + str(i[i['type']]['id']) + " "
                        elif i['type'] == "link":
                            atch +=  i['type'] + " " + i[i['type']]['title'] + " "
                        else:
                            atch += i['type'] + str(i[i['type']]['owner_id']) + \
                                "_" + str(i[i['type']]['id']) + " "
                    log_msg += atch
                dan63047VKbot.log(False, log_msg)
                dan63047VKbot.debug_array['messages_get'] += 1
                if event.message.peer_id not in dan63047VKbot.bot:
                    u = dan63047VKbot.db.get_all_users()
                    if str(event.message.peer_id) not in u:
                        dan63047VKbot.bot[user_id] = dan63047VKbot.VkBot(event.message.peer_id)
                    else:
                        i = dan63047VKbot.db.get_from_users(event.message.peer_id)
                        dan63047VKbot.bot[event.message.peer_id] = dan63047VKbot.VkBot(event.message.peer_id)
                dan63047VKbot.bot[event.message.peer_id].get_message(event)
            elif event.type == dan63047VKbot.VkBotEventType.WALL_POST_NEW:
                if event.object.post_type == "post":
                    dan63047VKbot.log(False, f"[NEW_POST] id{event.object.id}")
                    users = dan63047VKbot.db.get_all_users()
                    for i in users:
                        dan63047VKbot.bot[int(i)].event("post", event.object)
                else:
                    dan63047VKbot.log(False, f"[NEW_OFFER] id{event.object.id}")
            elif event.type == dan63047VKbot.VkBotEventType.MESSAGE_DENY:
                dan63047VKbot.log(False,
                    f"User {event.object.user_id} deny messages from that group")
                del dan63047VKbot.bot[int(event.object.user_id)]
                dan63047VKbot.db.delete_user(event.object.user_id)
            else:
                dan63047VKbot.log(False, f"Event {str(event.type)} happend")
        except Exception as kek:
            dan63047VKbot.log(True, f"Беды с ботом: {str(kek)}")
            dan63047VKbot.debug_array['bot_warnings'] += 1
            continue


def midnight():
    while True:
        current_time = time.time()+10800
        if int(current_time) % 86400 == 0:
            dan63047VKbot.log(False, "[EVENT_STARTED] \"Midnight\"")
            users = dan63047VKbot.db.get_all_users()
            for i in users:
                dan63047VKbot.bot[int(i)].event("midnight")
            dan63047VKbot.log(False, "[EVENT_ENDED] \"Midnight\"")
            time.sleep(1)
        else:
            time.sleep(0.50)


dan63047VKbot.SPAMMER_LIST = dan63047VKbot.db.read_spammers()
tread_bots = threading.Thread(target=bots)
tread_midnight = threading.Thread(target=midnight, daemon=True)
tread_bots.start()
tread_midnight.start()