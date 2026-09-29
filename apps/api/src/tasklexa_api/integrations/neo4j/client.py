from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str, driver: AsyncDriver | None = None) -> None:
        self._driver = driver or AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def run(self, query: str, **params: Any) -> list[dict]:
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return [record.data() async for record in result]

    async def verify_connectivity(self) -> None:
        await self._driver.verify_connectivity()

    async def close(self) -> None:
        await self._driver.close()
