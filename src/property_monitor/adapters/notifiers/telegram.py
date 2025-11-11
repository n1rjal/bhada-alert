class TelegramNotifier:
    """
    Notify user about room rent alert in telegram


    """

    def __init__(
        self,
        chat_id,
        group_id,
        telegram_token,
    ) -> None:
        """ """
        self.chat_id = chat_id
        self.telegram_token = telegram_token
