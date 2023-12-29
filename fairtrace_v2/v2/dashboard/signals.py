from django.db.models.signals import post_save
from django.dispatch import receiver
from v2.dashboard import cache_handlers
from v2.products.models import Batch


@receiver(post_save)
def rebuild_cache_with_theme(sender, instance, **kwargs):
    """To perform function rebuild_cache_with_theme."""
    sender_name = sender.__name__
    _id = None
    if sender_name == "CITheme":
        _id = instance.id
    if sender_name in ["ConsumerInterfaceProduct", "ConsumerInterfaceStage"]:
        _id = instance.theme.id
    if sender_name == "Program":
        theme = instance.program_themes.last()
        if theme:
            _id = theme.id
    if _id:
        batch_ids = cache_handlers.get_batches(_id)
        batches = Batch.objects.filter(pk__in=batch_ids)
        for batch in batches:
            cache_handlers.clear_ci_map_cache.delay(batch.id)
            cache_handlers.clear_ci_stage_cache.delay(batch.id)
            cache_handlers.clear_ci_claim_cache.delay(batch.id)
