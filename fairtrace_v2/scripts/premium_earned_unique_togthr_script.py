"""Dddddsd."""
from v2.projects.models import PremiumEarned
from v2.transactions.models import Transaction

earnings = list(PremiumEarned.objects.all())
for earn in earnings:
    earned = PremiumEarned.objects.filter(
        node=earn.node, premium=earn.premium, transaction=earn.transaction
    )
    if earned.count() > 1:
        duplicates = earned.exclude(id=earned.first().id)
        for dup in duplicates:
            earnings.remove(dup)

pe_ids = []
for e in earnings:
    pe_ids.append(e.id)

pes = PremiumEarned.objects.filter(id__in=pe_ids)

for txn in Transaction.objects.filter(transaction_type=1):
    if PremiumEarned.objects.filter(transaction=txn).exists():
        unq = pes.filter(transaction=txn)
        if unq.count() == 2:
            if unq[0].premium == unq[1].premium:
                print("we have issue")
        elif unq.count() == 1:
            pass
        else:
            print("more count", unq.count())
            print(unq)

pes = PremiumEarned.objects.filter(id__in=pe_ids)
dup = PremiumEarned.objects.all().exclude(id__in=pes)
print(
    "original: ",
    pes.count(),
    " dup : ",
    dup.count(),
    " total qs: ",
    PremiumEarned.objects.all().count(),
    " sum: ",
    pes.count() + dup.count(),
)
