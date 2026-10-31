# expected findings: DIP (class instantiating its dependencies internally
# instead of receiving them), docstrings.1 (missing docstrings).


class StripeGateway:
    def charge(self, amount):
        return amount


class MysqlOrderRepository:
    def save(self, order):
        return True


class CheckoutService:
    def __init__(self):
        self.gateway = StripeGateway()
        self.repo = MysqlOrderRepository()

    def checkout(self, order, amount):
        self.gateway.charge(amount)
        self.repo.save(order)
