<?php
// expected findings: acronym casing (Api -> API), missing docblocks.

class ApiClient
{
    public function fetchDataFromRemoteEndpoint($url, $method, $headers, $body, $timeout, $retries)
    {
        return [$url, $method, $headers, $body, $timeout, $retries];
    }
}
