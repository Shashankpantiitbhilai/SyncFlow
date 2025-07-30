#!/usr/bin/env python3
import asyncio
import asyncpg

async def test_simple():
    try:
        conn = await asyncpg.connect(
            "postgresql://zenskar_user:simple123@localhost:5432/zenskar_db"
        )
        result = await conn.fetchval("SELECT current_user")
        print(f"✅ SUCCESS: Connected as {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

asyncio.run(test_simple())
