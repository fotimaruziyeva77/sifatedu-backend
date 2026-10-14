import logging

from celery import shared_task

from .models import QuizDraft

logger = logging.getLogger(__name__)


# Gemini 30–90 s javob beradi: `ai` navbati (`worker-ai`), qayta urinilmaydi — o'qituvchi
# xato xabarini ko'radi va faylni qayta yuklaydi.
@shared_task(acks_late=False, soft_time_limit=170, time_limit=200)
def generate_draft(draft_id: int) -> None:
    """Qo'llanmadan test tuzish (`drafts.run`)."""
    from . import drafts

    draft = QuizDraft.objects.filter(pk=draft_id, status=QuizDraft.Status.PENDING).first()
    if draft is None:
        return
    try:
        drafts.run(draft)
    except Exception:
        logger.exception("Test tuzilmadi (qoralama %s)", draft_id)
        QuizDraft.objects.filter(pk=draft_id).update(
            status=QuizDraft.Status.FAILED, error="Test tuzilmadi. Qayta urinib ko'ring."
        )
