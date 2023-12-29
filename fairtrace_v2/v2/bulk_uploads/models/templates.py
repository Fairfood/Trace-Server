from common.currencies import CURRENCY_CHOICES
from common.models import AbstractBaseModel
from django.db import models

from .. import constants
from ..managers import DataSheetTemplateQuerySet
from ..schemas.farmer_upload_schema import FarmerUploadSchema
from ..schemas.trace_upload_schema import TraceFarmerUploadSchema, \
    TraceTransactionUploadSchema
from ..schemas.transaction_upload_schema import TransactionUploadSchema
from ...products import constants as product_const
from .common import get_file_path


class DataSheetTemplate(AbstractBaseModel):
    """Data sheet template model.

    This model represents a data sheet template used for importing data.
    It defines fields for the name of the template, the row numbers for the
    title and data rows, the file field for uploading the template file,
    the type of the template, the visibility of the template, and a flag
    indicating whether the template is deleted or not.

    Attributes:
        name (str): The name of the data sheet template.
        title_row (int): The row number where the title is located in the
            template.
        data_row (int): The row number where the data starts in the template.
        file (FileField): The file field for uploading the template file.
        type (int): The type of the template, chosen from
            TEMPLATE_TYPE_CHOICES.
        visibility (int): The visibility of the template, chosen from
            TEMPLATE_VISIBILITY_CHOICES.
        product (Product): The default product associated with the template.
        supply_chain (SupplyChain): The default supply chain associated with
            the template.
        currency (str): The default currency associated with the template.
        unit (int): The default unit of measurement associated with the
            template, chosen from UNIT_CHOICES.
        is_default (bool): A flag indicating whether the template is the
            default template.
        is_deleted (bool): A flag indicating whether the template is deleted or
            not.
        is_active (bool): A flag indicating whether the template is active
            or ready for creating uploads.
        is_system_template (bool): A flag indicating whether the template is
            a system template, that is, a template that is created by the
            system and cannot be deleted.
    """

    name = models.CharField(max_length=100)
    title_row = models.IntegerField(default=0)
    data_row = models.IntegerField(default=1)
    file = models.FileField(upload_to=get_file_path, blank=True, null=True,
                            max_length=255)
    type = models.IntegerField(
        choices=constants.TEMPLATE_TYPE_CHOICES,
        default=constants.TEMPLATE_TYPE_TXN,
    )
    visibility = models.IntegerField(
        choices=constants.TEMPLATE_VISIBILITY_CHOICES,
        default=constants.TEMPLATE_VISIBILITY_HIDDEN,
    )
    product = models.ForeignKey("products.Product",
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True)
    supply_chain = models.ForeignKey("supply_chains.SupplyChain",
                                     on_delete=models.SET_NULL,
                                     null=True,
                                     blank=True)
    unit = models.IntegerField(
        choices=product_const.UNIT_CHOICES,
        default=product_const.UNIT_KG,
        null=True, blank=True
    )
    currency = models.CharField(
        choices=CURRENCY_CHOICES,
        max_length=5, null=True, blank=True
    )
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_system_template = models.BooleanField(default=False)

    objects = DataSheetTemplateQuerySet.as_manager()

    def __str__(self):
        return f"DataSheetTemplate: {self.name} | {self.pk}"

    @property
    def schema(self):
        """Return the schema for the template.

        This cached property returns the schema for the template. It retrieves
        the 'FarmerUploadSchema' class and creates a modified schema based on
        the field positions defined in the 'field_positions' attribute of the
        template.

        Returns:
            type: The schema class for the template.

        Raises:
            Exception: If no fields are found for the template.
        """
        schema_mapping = {
            constants.TEMPLATE_TYPE_TXN: TransactionUploadSchema,
            constants.TEMPLATE_TYPE_CONNECTION: FarmerUploadSchema,
        }

        trace_schema_mapping = {
            constants.TEMPLATE_TYPE_TXN: TraceTransactionUploadSchema,
            constants.TEMPLATE_TYPE_CONNECTION: TraceFarmerUploadSchema
        }

        field_positions = self.field_positions.keys()
        if not field_positions:
            raise Exception("No fields found for this template.")

        # Get the schema class based on the template type.
        if self.is_system_template:
            schema = trace_schema_mapping.get(self.type)
        else:
            schema = schema_mapping.get(self.type)

        return schema.create_modified_schema(field_positions)

    @property
    def field_positions(self):
        """Return a dictionary of field names and their column positions.

        This property returns a dictionary of field names and their
        corresponding column positions. It retrieves the field names and
        column names from the 'fields' attribute of the template and creates a
        dictionary mapping the field names to their column positions.

        Returns:
            dict: A dictionary mapping field names to their column positions.
        """
        return dict(self.fields.values_list("name", "column_name"))  # noqa

    @property
    def indexed_fields(self):
        """Return a dictionary of column positions and their field names.

        This property returns a dictionary of column positions and their
        corresponding field names. It retrieves the field names and column
        positions from the 'fields' attribute of the template and creates a
        dictionary mapping the column positions to their field names.

        Returns:
            dict: A dictionary mapping column positions to their field names.
        """
        return dict(self.fields.values_list("column_pos", "name"))  # noqa


class DataSheetTemplateField(AbstractBaseModel):
    """Data sheet template field model.

    This model represents a field in a data sheet template. It is associated
    with a specific data sheet template through a foreign key relationship. The
    field has attributes for the name, type, required flag, column position,
    and column name.

    Attributes:
        template (DataSheetTemplate): The data sheet template associated with
            the field.
        name (str): The name of the field.
        type (str): The type of the field.
        required (bool): A flag indicating whether the field is required or
            not.
        column_pos (int): The position of the field's column in the data sheet.
        column_name (str): The name of the field's column.
    """

    template = models.ForeignKey(
        DataSheetTemplate, on_delete=models.CASCADE, related_name="fields"
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    required = models.BooleanField(default=False)
    column_pos = models.IntegerField()
    column_name = models.CharField(max_length=100)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.template.name}: {self.name} | {self.pk}"


class NodeDataSheetTemplates(AbstractBaseModel):
    """Node data sheet templates model.

    This model represents the mapping of data sheet templates to nodes. It is
    associated with a specific node and data sheet template through foreign key
    relationships. The model also has a status field indicating the status of
    the mapping.

    Attributes:
        node (Node): The node associated with the data sheet template mapping.
        template (DataSheetTemplate): The data sheet template associated with
            the node.
        status (int): The status of the data sheet template mapping, chosen
            from NODE_TEMPLATE_STATUS_CHOICES.
    """

    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="map_templates",
        null=True,
        blank=True,
        default=None,
    )

    template = models.ForeignKey(
        DataSheetTemplate,
        on_delete=models.CASCADE,
        related_name="map_nodes",
        null=True,
        blank=True,
        default=None,
    )
    status = models.IntegerField(
        choices=constants.NODE_TEMPLATE_STATUS_CHOICES,
        default=constants.NODE_TEMPLATE_STATUS_ACTIVE,
    )

    def __str__(self):
        return f"{self.template.name}: {self.node.full_name} | {self.pk}"
