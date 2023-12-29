# Generated by Django 2.2.6 on 2021-03-14 18:05
import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("products", "0001_initial"),
        ("claims", "0001_initial"),
        ("blockchain", "0001_initial"),
        ("transactions", "0001_initial"),
        ("supply_chains", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="transactionclaim",
            name="transaction",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="claims",
                to="transactions.Transaction",
            ),
        ),
        migrations.AddField(
            model_name="transactionclaim",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_transactionclaim_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="transactionclaim",
            name="verifier",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions_verifications",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="fieldresponse",
            name="added_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="fieldresponse",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_fieldresponse_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="fieldresponse",
            name="criterion",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="field_responses",
                to="claims.AttachedCriterion",
            ),
        ),
        migrations.AddField(
            model_name="fieldresponse",
            name="field",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="claims.CriterionField",
            ),
        ),
        migrations.AddField(
            model_name="fieldresponse",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_fieldresponse_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="criterionfield",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_criterionfield_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="criterionfield",
            name="criterion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fields",
                to="claims.Criterion",
            ),
        ),
        migrations.AddField(
            model_name="criterionfield",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_criterionfield_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="criterion",
            name="claim",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="criteria",
                to="claims.Claim",
            ),
        ),
        migrations.AddField(
            model_name="criterion",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_criterion_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="criterion",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_criterion_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="claimcomment",
            name="attached_claim",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to="claims.AttachedClaim",
            ),
        ),
        migrations.AddField(
            model_name="claimcomment",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_claimcomment_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="claimcomment",
            name="sender",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="claimcomment",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_claimcomment_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="block_chain_request",
            field=models.OneToOneField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="claims_claim",
                to="blockchain.BlockchainRequest",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_claim_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="owners",
            field=models.ManyToManyField(
                blank=True,
                related_name="claims_owned",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="supply_chains",
            field=models.ManyToManyField(
                blank=True, to="supply_chains.SupplyChain"
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_claim_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="verifiers",
            field=models.ManyToManyField(
                blank=True,
                related_name="verifiable_claims",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="attachedcriterion",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_attachedcriterion_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="attachedcriterion",
            name="criterion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attached_criteria",
                to="claims.Criterion",
            ),
        ),
        migrations.AddField(
            model_name="attachedcriterion",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_attachedcriterion_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="attached_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="claims_attached",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="claim",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="claims.Claim"
            ),
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_attachedclaim_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_attachedclaim_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="verifier",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="claim_verifications",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="attachedcompanycriterion",
            name="company_claim",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="criteria",
                to="claims.AttachedCompanyClaim",
            ),
        ),
        migrations.AddField(
            model_name="attachedcompanyclaim",
            name="node",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="claims",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="attachedbatchcriterion",
            name="batch_claim",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="criteria",
                to="claims.AttachedBatchClaim",
            ),
        ),
        migrations.AddField(
            model_name="attachedbatchclaim",
            name="batch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="claims",
                to="products.Batch",
            ),
        ),
        migrations.AddField(
            model_name="attachedbatchclaim",
            name="block_chain_request",
            field=models.OneToOneField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="claims_attachedbatchclaim",
                to="blockchain.BlockchainRequest",
            ),
        ),
    ]
