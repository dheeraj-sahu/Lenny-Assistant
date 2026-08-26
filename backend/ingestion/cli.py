"""
ingestion/cli.py

CLI entrypoint for the ingestion pipeline.
Usage:
    python -m ingestion.cli

Can also be called via the admin HTTP endpoint POST /admin/refresh-kb.
"""

import asyncio
import sys

from core.logging import configure_logging, get_logger
from ingestion.ingest_pipeline import run_ingestion_pipeline

logger = get_logger(__name__)


async def main() -> None:
    configure_logging("INFO")
    logger.info("ingestion_cli_start")

    result = await run_ingestion_pipeline()

    if result["status"] == "success":
        logger.info("ingestion_cli_success", **result)
        print(
            f"\n✅ Ingestion complete:\n"
            f"   Episodes : {result['episode_count']}\n"
            f"   Chunks   : {result['chunk_count']}\n"
            f"   Commit   : {result['commit_sha'][:8] if result['commit_sha'] else 'n/a'}\n"
        )
        sys.exit(0)
    else:
        logger.error("ingestion_cli_failed", **result)
        print(f"\n❌ Ingestion failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
