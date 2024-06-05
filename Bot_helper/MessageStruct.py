class MessageStruct:
    def __init__(self, text_message, uid, time_send, deep_link, chat_id):
        self.deep_link = deep_link
        self.time_send = time_send
        self.uid = uid
        self.text_message = text_message
        self.chat_id = chat_id

    def to_json(self):
        return {
            "uid": f"{self.uid}",
            "deep_link": f"{self.deep_link}",
            "chat_id": f"{self.chat_id}",
            "time_send": f"{self.time_send}",
            "text_message": f"{self.text_message}"
            }
