import logging

logger = logging.getLogger(__name__)


def log_comment_created(
    *,
    comment_id: int,
    task_id: int,
    author_id: int,
) -> None:
    logger.info(
        "Background event: comment created comment_id=%s task_id=%s author_id=%s",
        comment_id,
        task_id,
        author_id,
    )
