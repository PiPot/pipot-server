from pipot.notifications.INotification import INotification


class TelegramNotification(INotification):
    def __init__(self, config):
        super(TelegramNotification, self).__init__(config)

    def process(self, message):
        for chat_id in self.config['chat_ids']:
            self.bot.send_message(chat_id, message)

    @staticmethod
    def get_pip_dependencies():
        return ['python-telegram-bot']

    @staticmethod
    def after_install_hook():
        return True

    @staticmethod
    def get_apt_dependencies():
        return []

    def requires_extra_config(self):
        return True

    def is_valid_extra_config(self, config):
        return 'token' in config and 'chat_ids' in config

    @staticmethod
    def get_extra_config_sample():
        return {
            'token': '123456:ABC',
            'chat_ids': [123456, 1234567]
        }

    @staticmethod
    def modified_function_for_test():
        pass
