# HTTP APIs

## Status codes 401 and 403

401 Unauthorized means the client is not authenticated: the credentials are missing or invalid, so it should log in and retry. 403 Forbidden means the server knows who the client is, but that identity is not allowed to access the resource.

## Rate limiting

When a client sends too many requests, the server answers 429 Too Many Requests. A well-behaved server includes a Retry-After header telling the client how many seconds to wait before trying again.

## Idempotency

An operation is idempotent when repeating it has the same effect as doing it once. GET, PUT and DELETE are idempotent; POST is not, which is why payment APIs accept an idempotency key so that retries do not charge a card twice.

## CORS

Browsers block cross-origin requests unless the server opts in with CORS headers. For non-simple requests the browser first sends a preflight OPTIONS request and checks the Access-Control-Allow-Origin and Access-Control-Allow-Methods headers in the response.

## Pagination

Offset pagination with LIMIT and OFFSET gets slow on deep pages and can skip or repeat items when rows change. Cursor-based pagination returns an opaque cursor pointing at the last item seen, which stays fast and stable.

## Caching with ETags

A server can send an ETag that identifies a version of a resource. The client sends it back in an If-None-Match header, and if nothing changed the server replies 304 Not Modified with an empty body, saving bandwidth.
