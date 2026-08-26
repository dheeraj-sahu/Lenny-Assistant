"""
core/logging.py

Structured JSON logging setup using Python's standard logging + structlog.
Every log line is a JSON object so it can be ingested by any log aggregator.
Each request gets a unique request_id that is injected by the middleware and
propagates to every log line emitted during that request.
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Call this once at application startup (in main.py lifespan).
    After this, use `structlog.get_logger()` everywhere.
    """

    # Structlog processors chain
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,          # picks up request_id etc.
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Final renderer: JSON in production, colored console in dev
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Convenience wrapper — import this instead of structlog.get_logger()."""
    return structlog.get_logger(name)
