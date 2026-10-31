<?php
// expected findings: DIP (new Dep() inside class methods),
// missing docblocks.

class StripeGateway
{
    public function charge($amount)
    {
        return $amount;
    }
}

class MysqlOrderRepository
{
    public function save($order)
    {
        return true;
    }
}

class CheckoutService
{
    private $gateway;
    private $repo;

    public function __construct()
    {
        $this->gateway = new StripeGateway();
        $this->repo = new MysqlOrderRepository();
    }
}
