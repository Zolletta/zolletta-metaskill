<?php
// expected findings: bad test names / structure for php-aware testing
// scanners.

class WhateverTest
{
    public function testIt()
    {
        assert(true);
    }

    public function test1()
    {
        assert(1 + 1 === 2);
    }
}
