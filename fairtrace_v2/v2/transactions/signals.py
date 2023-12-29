# @receiver(post_save)
# def caching_signal_transaction(sender, instance, **kwargs):
#     sender_name = sender.__name__
#     batches = []
#     if sender_name in ('Transaction', 'ExternalTransaction',
#                        'InternalTransaction'):
#         batches = instance.source_batches.all()
#         if batches:
#             batches = batches[:1]
#
#     for batch in batches:
#         clear_ci_cache(batch, 'stage')
#         clear_ci_cache(batch, 'map')
