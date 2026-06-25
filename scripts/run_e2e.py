import asyncio
import os
from main import _run_pipeline

os.environ["GROQ_API_KEY"] = "fake-key"
os.environ["MULTI_AGENT"] = "true"

async def test_trace():
    print("Running pipeline...")
    try:
        await _run_pipeline(
            "test/repo", 1, "diff --git a/test.py b/test.py\n+++ b/test.py\n@@ -1,1 +1,2 @@\n-x=1\n+x=2", False
        )
    except Exception as e:
        print("Pipeline errored as expected:", type(e))

if __name__ == "__main__":
    asyncio.run(test_trace())
