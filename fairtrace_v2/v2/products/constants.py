from django.utils.translation import gettext_lazy as _

# Product types
PRODUCT_TYPE_GLOBAL = 1
PRODUCT_TYPE_LOCAL = 2
#for products like carbon token
PRODUCT_TYPE_CARBON = 3

PRODUCT_TYPE_CHOICES = (
    (PRODUCT_TYPE_GLOBAL, "Global"),
    (PRODUCT_TYPE_LOCAL, "Local"),
    (PRODUCT_TYPE_CARBON, "Carbon")
)

UNIT_KG = 1
UNIT_TONNE = 2
UNIT_METRIC_TON_CO2E = 3

UNIT_CHOICES = (
    (UNIT_KG, "KG"), 
    (UNIT_TONNE, "Tonne"), 
    (UNIT_METRIC_TON_CO2E, "Metric Ton of CO2e")
)

UNIT_CONVERSION_FACTOR = {
    UNIT_KG: 1000,
    UNIT_TONNE: 1000000,
}

# Batch types
BATCH_TYPE_SOLID = 1
BATCH_TYPE_INTERMEDIATE = 2

BATCH_TYPE_CHOICES = (
    (BATCH_TYPE_SOLID, "Solid"),
    (BATCH_TYPE_INTERMEDIATE, "Intermediate"),
)

# Batch Source type
BATCH_SOURCE_TYPE_RECEIVED = 1
BATCH_SOURCE_TYPE_RETURNED = 2
BATCH_SOURCE_TYPE_PROCESSED = 3
BATCH_SOURCE_TYPE_MERGED = 4

BATCH_SOURCE_TYPE_CHOICES = (
    (BATCH_SOURCE_TYPE_RECEIVED, "Received"),
    (BATCH_SOURCE_TYPE_RETURNED, "Returned"),
    (BATCH_SOURCE_TYPE_PROCESSED, "Processed"),
    (BATCH_SOURCE_TYPE_MERGED, "Merged"),
)

OUTGOING_DESCRIPTION = _("Outgoing to %s")
INCOMING_DESCRIPTION = _("Incoming from %s")
PROCESSED_DESCRIPTION = _("Processed by %s")

OUTGOING = _("Outgoing")
INCOMING = _("Incoming")
PROCESSED = _("Processed")
INCOMING_AND_PROCESSED = _("Incoming and Outgoing")
