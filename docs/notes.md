[http://localhost/SupportHub/backend/api/v1/home/client-hours?date\_from=2026-09-01&date\_to=2026-09-20](http://localhost/SupportHub/backend/api/v1/home/client-hours?date_from=2026-09-01\&date_to=2026-09-20)
Request method
GET
Status code
500 Internal Server Error
Remote address
[::1]:80
Referrer policy
strict-origin-when-cross-orig

WebSocket connection to 'ws\://localhost/SupportHub/backend/api/v1/notifications/ws?ticket=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIiwidHlwZSI6Im5vdGlmaWNhdGlvbnNfd2Vic29ja2V0IiwiaWF0IjoxNzg5ODU1Nzc0LCJleHAiOjE3ODk4NTU4MDR9.C2IURHUNSsJzvOEZqAPkKCOsL-iohu7N214VfyCQxtw' failed: Error during WebSocket handshake: 'Sec-WebSocket-Accept' header is missing
```
"error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred.",
    "details": {},
    "correlation_id": "7d987362-c28d-4c5e-857b-371f47f66fe2"
}
```

}

I’ll trace the 500 using the correlation ID and review the endpoint’s database queries. I’ll check the WebSocket error separately, since it may have a different cause.

I found a concrete failure path: the endpoint builds its client lookup from active clients, then indexes it with every closed ticket. A ticket for an inactive client raises a KeyError and returns 500. I’m fixing that path and tightening the queries for larger customer datasets.




Edited file

routes.py+23-15











You've hit your usage limit. Upgrade your plan or add credits to continue, or try again at 3:28 AM.






  Edited routes.py+23-15Review changesUndoReview