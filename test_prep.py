import asyncio
from httpx import AsyncClient

async def test():
    async with AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        # Test today
        res = await client.get("/kds/prep-list?target_date=2026-09-14")
        print("Today:", res.status_code, len(res.json().get("components", [])))
        # Test tomorrow
        res = await client.get("/kds/prep-list?target_date=2026-09-15")
        print("Tomorrow:", res.status_code, len(res.json().get("components", [])))

asyncio.run(test())
