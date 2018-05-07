import telegram


class TmTelegram:

    def __init__(self, token, chats, logging):
        """Init var."""
        self.logging = logging
        self.logging.info("Initiliaze telegram bot")
        self.bot = telegram.Bot(token=token)
        self.chats = chats

    def send_telegram(self, message):
        """Send telegram message."""
        self.logging.info("Sending file and message to telegram.")
        for item in self.chats:
            try:
                self.bot.send_message(chat_id=item,
                                      text=message,
                                      parse_mode=telegram.ParseMode.HTML)

            except Exception as e:
                print(e.__doc__)
                print(e.message)