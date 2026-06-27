from __future__ import annotations

import asyncio
import logging
from typing import Callable, TypeVar

logger = logging.getLogger("termorganism.llm.retry")

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> T:
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"LLM call failed after {max_retries} attempts: {e}")
    raise last_exception
