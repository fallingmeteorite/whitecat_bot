def unwrap_quote(m):
    return m.replace("&", "&").replace("[", "[").replace("]", "]").replace(",", ",")


def handle_message(message):
    if "post_type" not in message or message['post_type'] != "message":
        return None

    if message["message"][0]["type"] == "text":
        message["message"][0]["data"]["text"] = unwrap_quote(message["message"][0]["data"]["text"])

    # 提取数据
    uid = message["user_id"]
    nickname = message["sender"]["nickname"]
    gid = message.get("group_id", None)
    message_dict = {
        "raw_message": unwrap_quote(message["raw_message"]),
        "message": message["message"][0],
        'message_id': message.get('message_id', None)
    }

    return uid, nickname, gid, message_dict
