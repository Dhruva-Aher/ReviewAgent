import os
import json
import time
import logging
import asyncio

from agents.base import AgentContext
from orchestrator import run_multi_agent_review

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("queue_worker")

try:
    import redis
except ImportError:
    raise ImportError("The 'redis' package is required to run the queue worker. Please install it with 'pip install redis'")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

def get_redis():
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)

async def process_job(job_dict: dict):
    logger.info(f"Processing job for PR #{job_dict.get('pr_number')} in {job_dict.get('repo')}")

    # build AgentContext correctly from the job dict
    context = AgentContext(
        diff=job_dict.get("diff", ""),
        beliefs_text=job_dict.get("beliefs_text", ""),
        repo=job_dict.get("repo", ""),
        pr_number=job_dict.get("pr_number", 0),
        pr_title=job_dict.get("pr_title", ""),
        pr_description=job_dict.get("pr_description", ""),
        changed_files=job_dict.get("changed_files", []),
        config=job_dict.get("config", {})
    )

    agents_to_run = ["SecurityAgent", "ArchitectureAgent", "PerformanceAgent", "TestCoverageAgent", "DependencyAgent"]
    await run_multi_agent_review(context, agents_to_run)
    logger.info(f"Finished processing PR #{context.pr_number}")

def run_worker():
    r = None
    while True:
        try:
            if not r:
                r = get_redis()
                r.ping()
                logger.info("Connected to Redis")

            # blpop handles queue blocking
            result = r.blpop("pr_review_queue", timeout=5)
            if result:
                queue_name, job_data = result
                job_dict = json.loads(job_data)
                job_id = job_dict.get("job_id")

                try:
                    asyncio.run(process_job(job_dict))
                    if job_id:
                        r.set(f"job_status:{job_id}", "completed")
                except Exception as e:
                    logger.error(f"Error processing job: {e}")
                    if job_id:
                        r.set(f"job_status:{job_id}", "failed")

        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            logger.warning(f"Redis connection drop: {e}. Retrying in 5 seconds...")
            r = None
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_worker()
