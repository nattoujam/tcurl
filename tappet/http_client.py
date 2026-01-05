import httpx

from tappet.models import RequestSet, Response


async def execute_request(request_set: RequestSet) -> Response:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.request(
                request_set.method,
                request_set.url,
                headers=request_set.headers,
                json=request_set.body if request_set.body else None,
            )
    except Exception as exc:
        return Response(error=str(exc))

    elapsed_ms = None
    if response.elapsed is not None:
        elapsed_ms = response.elapsed.total_seconds() * 1000
    return Response(
        status_code=response.status_code,
        reason=response.reason_phrase,
        headers=dict(response.headers),
        body=response.text,
        elapsed_ms=elapsed_ms,
    )
