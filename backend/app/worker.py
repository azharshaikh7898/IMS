from __future__ import annotations

import asyncio
import json
import logging
from app.models.schemas import Severity, SignalIngestRequest
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db import lifespan_database
from app.api.deps import build_container

logger = logging.getLogger(__name__)


async def process_with_retry(services, payload: dict[str, str], max_attempts: int = 3) -> None:
    signal = SignalIngestRequest(
        component_id=payload["component_id"],
        severity=Severity(payload["severity"]),
        source="stream",
        summary=payload["summary"],
        payload={},
    )

    for attempt in range(1, max_attempts + 1):
        try:
            await services.debouncer.process_signal(signal, payload["signal_id"])
            return
        except Exception as exc:
            if attempt == max_attempts:
                raise
            delay = 0.2 * (2 ** (attempt - 1))
            logger.warning(
                "retrying_signal_processing attempt=%s signal_id=%s delay_s=%.2f error=%s",
                attempt,
                payload.get("signal_id"),
                delay,
                exc,
            )
            await asyncio.sleep(delay)


async def consume_signals() -> None:
    configure_logging()
    settings = get_settings()
    async with lifespan_database(settings) as bundle:
        services = build_container(bundle)
        redis = services.cache.redis
        try:
            await redis.xgroup_create(settings.worker_stream, "ims-workers", id="0-0", mkstream=True)
        except Exception:
            pass
        while True:
            try:
                events = await redis.xreadgroup("ims-workers", "worker-1", {settings.worker_stream: ">"}, count=100, block=5000)
            except Exception as exc:
                logger.warning("worker_stream_read_failed error=%s", exc)
                await asyncio.sleep(1)
                continue

            for stream_name, stream_events in events:
                for event_id, payload in stream_events:
                    try:
                        await process_with_retry(services, payload)
                        await redis.xack(settings.worker_stream, "ims-workers", event_id)
                        logger.info("processed_signal=%s", payload.get("signal_id"))
                    except Exception as exc:
                        # Intentionally do not ack failed events: they remain pending for replay/recovery.
                        logger.error(
                            "signal_processing_failed signal_id=%s event_id=%s error=%s",
                            payload.get("signal_id"),
                            event_id,
                            exc,
                        )
            await asyncio.sleep(0.05)


def main() -> None:
    asyncio.run(consume_signals())


if __name__ == "__main__":
    main()
