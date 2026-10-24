# expected findings: ISP (fat ABC interface, >= 5 methods; implementer
# stubbing methods with NotImplementedError), docstrings.1 (missing
# docstrings), classes.3 (three classes in one file).
from abc import ABC, abstractmethod


class BroadChannel(ABC):
    @abstractmethod
    def send_email(self, to, subject, body):
        pass

    @abstractmethod
    def send_sms(self, number, message):
        pass

    @abstractmethod
    def send_push(self, device, title, payload):
        pass

    @abstractmethod
    def send_slack(self, channel, text):
        pass

    @abstractmethod
    def send_webhook(self, url, event, data):
        pass

    @abstractmethod
    def schedule_digest(self, user, frequency):
        pass


class NotificationService(BroadChannel):
    def send_email(self, to, subject, body):
        return f"email to {to}: {subject}"

    def send_sms(self, number, message):
        return f"sms to {number}: {message}"

    def send_push(self, device, title, payload):
        raise NotImplementedError

    def send_slack(self, channel, text):
        raise NotImplementedError

    def send_webhook(self, url, event, data):
        raise NotImplementedError

    def schedule_digest(self, user, frequency):
        raise NotImplementedError
