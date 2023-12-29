"""Models for bulk_templates."""
import os
import urllib
from datetime import datetime

import pandas as pd
from common.currencies import CURRENCY_CHOICES
from common.library import ChoiceAdapter
from common.models import AbstractBaseModel
from django.conf import settings
from django.contrib.postgres import fields
from django.db import models
from django.db.models import Q
from v2.bulk_templates import constants as temp_const
from v2.bulk_templates import validator
from v2.products import constants as product_const
from v2.supply_chains.models import BulkExcelUploads

from . import choices
from . import constants


# Create your models here.
def _get_file_path(instance, filename):
    """
    Function to get filepath for a file to be uploaded
    Args:
        instance: instance of the file object
        filename: uploaded filename

    Returns:
        path: Path of file
    """
    type = instance.__class__.__name__.lower()
    filename = os.path.splitext(filename)
    path = "%s/%s/%s:%s" % (
        type,
        instance.id,
        constants.CUSTOM_TEMP_NAME + "_",
        str(datetime.now().strftime("%d-%m-%Y_%H:%M:%S")) + str(filename[1]),
    )
    return path


class Template(AbstractBaseModel):
    """Model to save basic details of custom template of companies. companies
    can create their own bulk transaction excel templates to import
    transactions or connections.

    Attributes:
        nodes(obj)      : company objects that create template.
        name(str)       : name of template.
        title_row(str)  : row number where the title of the
                          template starts.
        data_row(str)   : row number where the data of the
                          template starts
        file(file)      : Uploaded file.
        type(int)       : type of template ie, what type of datas
                          are stored in this template. eg, template is
                          for txn or connection.
        visibility(int) : if template is accessible for all
                          companies then set visibility field as
                          public.
    """

    nodes = models.ManyToManyField(
        "supply_chains.Node",
        through="bulk_templates.NodeTemplate",
        related_name="templates",
    )
    name = models.CharField(max_length=100, default="", blank=True, null=True)
    title_row = models.IntegerField(null=True, blank=True, default=0)
    data_row = models.IntegerField(null=True, blank=True, default=0)
    file = models.FileField(upload_to=_get_file_path, blank=True, null=True)
    type = models.IntegerField(
        choices=constants.TEMPLATE_TYPE_CHOICES,
        default=constants.TEMPLATE_TYPE_TXN,
    )
    visibility = models.IntegerField(
        choices=constants.TEMPLATE_VISIBILITY_CHOICES,
        default=constants.TEMPLATE_VISIBILITY_HIDDEN,
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name} | {self.id}"

    def save_temp_excel(self):
        """save excel to a local path for read a saved file."""
        # file_path = 'https://fairtrace-v2-development.s3.amazonaws.com
        # /media/template/None/
        # e3jRtDzbvKtransaction_upload_bulk_raw_pepper.xlsx'
        if settings.ENVIRONMENT == "local":
            url = "file://" + settings.BASE_DIR + self.file.url
        else:
            url = self.file.url
        urllib.request.urlretrieve(url, temp_const.TEMP_FILE)
        file_path = str(os.getcwd()) + "/" + temp_const.TEMP_FILE
        return file_path

    @property
    def filename(self):
        """Get filename."""
        return os.path.basename(self.file.name)

    def is_title_set(self):
        """Check title row is set or not."""
        if 0 in {self.title_row, self.data_row}:
            return False
        return True

    @classmethod
    def node_template_qs(cls, node):
        """Node template qs."""
        query = Q(nodes=node)
        query &= ~Q(visibility=constants.TEMPLATE_VISIBILITY_HIDDEN)
        query &= Q(is_deleted=False)
        return query


class NodeTemplate(AbstractBaseModel):
    """Model to represent which node is uploaded the custom template.

    Attributes:
       node(obj)           : Node that create template.
       template(obj)       : template object.
       status(int)         : Status of node template. status can be
                             active or inactive.
    """

    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        related_name="node_template",
        null=True,
        blank=True,
        default=None,
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name="node_templates",
        null=True,
        blank=True,
        default=None,
    )
    status = models.IntegerField(
        choices=constants.NODE_TEMPLATE_STATUS_CHOICES,
        default=constants.NODE_TEMPLATE_STATUS_INACTIVE,
    )
    product = models.ForeignKey(
        "products.Product", null=True, on_delete=models.SET_NULL
    )
    unit = models.IntegerField(
        choices=product_const.UNIT_CHOICES, default=product_const.UNIT_KG
    )
    currency = models.CharField(
        choices=CURRENCY_CHOICES,
        default=None,
        null=True,
        blank=True,
        max_length=5,
    )


class DynamicBulkUpload(BulkExcelUploads):
    """Model to store the uploaded files. save file datas and errors as json
    while reading excel. also track the progress of adding connections.

    Attributes:
       template(obj)       : template object.
    """

    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name="bulk_template",
        null=True,
        blank=True,
        default=None,
    )

    def save_temp_excel(self):
        """save excel to a local path for read a saved file."""
        # file_path = 'https://fairtrace-v2-development.s3.amazonaws.com
        # /media/template/None/
        # e3jRtDzbvKtransaction_upload_bulk_raw_pepper.xlsx'
        if settings.ENVIRONMENT == "local":
            url = "file://" + settings.BASE_DIR + self.file.url
        else:
            url = self.file.url
        urllib.request.urlretrieve(url, temp_const.TEMP_FILE)
        file_path = str(os.getcwd()) + "/" + temp_const.TEMP_FILE
        return file_path

    @property
    def filename(self):
        """Get filename."""
        return os.path.basename(self.file.name)


class TemplateTypeField(AbstractBaseModel):
    """Model to save field details of template. field have different properties
    like name, type, description etc. also can set field is required or not.

    Attributes:
        optional_with(obj)  : object that store the alternative
                              field of template field. eg, if field
                              name fairID is null then can replace it
                              with TraceID.so if fairID is the field
                              name,then optional_with should be
                              traceID or if first_name is field name
                              then optional_with should be first_name
                              itself. bcz there is no other optional
                              field for first_name.
        template_type(int)  : type of template ie, what type of data
                              are stored in this field. eg, txn data
                              or connection.
        name(str)           : name of field.
        type(int)           : type of field. eg: char, int etc.
        description(str)    : description of field.
        required(bool)      : set field is required or not.

    Example:
        if fairID is the field then model fields are:
            {
            optional_with: object of traceID field,
            required: True,
            name:  fairID,
            description: field for save farmer id,
            template_type: 1 (TEMPLATE_TYPE_TXN),
            type: 3 (STRING),
            meta: {
                    fairID: 'field from node model',

                   }
            }
    """

    optional_with = models.ForeignKey(
        "self", blank=True, null=True, on_delete=models.SET_NULL
    )
    required = models.BooleanField(default=False)
    name = models.CharField(max_length=500)
    description = models.CharField(max_length=1000, default="", blank=True)
    template_type = models.IntegerField(
        choices=constants.TEMPLATE_TYPE_CHOICES,
        default=constants.TEMPLATE_TYPE_TXN,
    )
    type = models.IntegerField(
        choices=ChoiceAdapter(choices.FieldType),
        default=choices.FieldType.STRING.value,
    )
    meta = fields.JSONField(null=True, blank=True, default=dict)
    key = models.CharField(max_length=1000)
    span = models.IntegerField(
        choices=constants.FIELD_SPAN_CHOICES, default=constants.FIELD_SPAN_HALF
    )

    class Meta:
        unique_together = (
            "name",
            "key",
        )

    def __str__(self):
        """To perform function __str__."""
        return f"{self.name} {self.type} - {self.description} | {self.id}"


class TemplateField(AbstractBaseModel):
    """model to store the column position of each template field. user can
    select the column and field with their own choice when creating a template.

    Attributes:
       template(obj)       : template object.
       field(obj)          : template type field object.
       column_pos(str)     : column position of a field that the user
                             select when creating custom template.
    """

    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name="template_fields",
        null=True,
        blank=True,
        default=None,
    )
    field = models.ForeignKey(
        TemplateTypeField,
        on_delete=models.CASCADE,
        related_name="template_field",
        null=True,
        blank=True,
        default=None,
    )
    column_pos = models.IntegerField(null=True, blank=True, default=0)

    def get_schema(self):
        """Get schema."""
        schema = {self.field.name: constants.SCHEMAS[self.field.type]}
        return schema

    def field_details(self):
        """Returns fields."""
        fields = {
            "label": self.field.name,
            "field_id": self.field.idencode,
            "type": self.field.type,
            "required": self.field.required,
            "span": self.field.span,
            "key": self.field.key,
            "meta": self.field.meta,
        }
        return fields

    def validate_data(self, col_data):
        """Function for validate field data using cerberus libray.

        and return validity and message
        """
        issue_count = 0
        message = ""
        validator_obj = validator.ExcelValidator()
        validator_obj.schema = self.get_schema()
        document = {self.field.name: col_data if col_data != "None" else None}
        type_fields = self.field_details()
        valid = validator_obj.validate(document)
        if type(col_data) == pd._libs.tslibs.timestamps.Timestamp:
            col_data = datetime.strftime(col_data.to_pydatetime(), "%Y-%m-%d")
        elif type(col_data) == datetime:
            col_data = datetime.strftime(col_data, "%Y-%m-%d")
        # set value as empty when date value is not valid
        if not valid:
            col_data = ""
            message = f"{{{self.field.name}: [Invalid {self.field.name}]}}"
            issue_count = 1
        type_fields.update(
            {"valid": valid, "value": col_data, "message": message}
        )
        return type_fields, issue_count
