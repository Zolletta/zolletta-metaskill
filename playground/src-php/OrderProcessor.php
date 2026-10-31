<?php
// expected findings: OCP (instanceof if/elseif ladder >= 3 branches),
// ISP (fat interface), classes.3 (six classes in one file),
// missing docblocks.

interface Worker
{
    public function process();
    public function validate();
    public function persist();
    public function notify();
    public function audit();
    public function rollback();
}

class UpsCarrier {}
class FedexCarrier {}
class DhlCarrier {}
class UspsCarrier {}

class OrderProcessor
{
    public function ship($order, $carrier)
    {
        if ($carrier instanceof UpsCarrier) {
            return 'ups label';
        } elseif ($carrier instanceof FedexCarrier) {
            return 'fedex label';
        } elseif ($carrier instanceof DhlCarrier) {
            return 'dhl label';
        } elseif ($carrier instanceof UspsCarrier) {
            return 'usps label';
        }
        throw new \InvalidArgumentException('unknown carrier');
    }
}
