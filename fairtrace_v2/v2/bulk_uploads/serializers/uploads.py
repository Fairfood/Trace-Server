from common.drf_custom.serializers import DynamicModelSerializer
from ..models.uploads import DataSheetUpload
from ..models.uploads import DataSheetUploadSummary
from ...products.serializers.product import ProductSerializer


class DataSheetUploadSummarySerializer(DynamicModelSerializer):
    """Serializer for the DataSheetUploadSummary model.

    This serializer provides serialization and deserialization
    functionality for instances of the DataSheetUploadSummary model. It
    includes all fields of the DataSheetUploadSummary model.
    """

    class Meta:
        model = DataSheetUploadSummary
        fields = "__all__"


class DataSheetUploadSerializer(DynamicModelSerializer):
    """Serializer for the DataSheetUpload model.

    This serializer provides serialization and deserialization
    functionality for instances of the DataSheetUpload model. It
    includes the DataSheetUploadSummarySerializer for the 'summary'
    field and excludes the 'file_hash', 'initial_data', 'data_hash',
    'is_used' and 'data' fields from serialization.
    """

    summary = DataSheetUploadSummarySerializer(
        read_only=True, exclude_fields=("upload",)
    )
    product_details = ProductSerializer(source="product", read_only=True,
                                        fields=("id", "name"))

    class Meta:
        model = DataSheetUpload
        exclude = (
            "file_hash", "initial_data", "data", "data_hash", 
            "added_transactions"
        )
