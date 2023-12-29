from v2.projects.models import NodeCard

for card in NodeCard.objects.all():
    try:
        NodeCard.objects.get(card_id=card.card_id)
    except Exception:
        NodeCard.objects.filter(card_id=card.card_id).first().delete()
