# Documentation for monitoring

## How many days until SSL certificate expires

```
curl "<http://localhost:9090/api/v1/query>" \
--data-urlencode \
'query=round(((probe_ssl_earliest_cert_expiry{job="blackbox-https"} - time())/86400)\*10)/10' | jq .`
```
