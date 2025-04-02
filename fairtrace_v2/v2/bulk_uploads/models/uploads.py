import numpy as np
import pandas as pd
from common.currencies import CURRENCY_CHOICES
from common.library import DateTimeEncoder, hash_file
from common.models import AbstractBaseModel
from django.contrib.postgres import fields
from django.db import models
from rest_framework.exceptions import ValidationError

from ...products import constants as product_const
from . import DataSheetTemplate
from .common import get_file_path


class DataSheetUpload(AbstractBaseModel):
    """Data sheet upload model.

    This model represents a data sheet upload. It is associated with a specific
     node, data sheet template, product, and unit. The model includes fields
     for the uploaded file, file hash, currency, initial data, processed data,
     data hash, errors, and a flag indicating whether the upload is used.

    Attributes:
        node (Node): The node associated with the data sheet upload.
        template (DataSheetTemplate): The data sheet template associated with
            the upload.
        file (FileField): The uploaded file.
        file_hash (str): The hash value of the uploaded file.
        product (Product): The product associated with the upload.
        supply_chain (SupplyChain): The supply chain associated with the
            upload.
        unit (int): The unit of measurement for the upload, chosen from
            UNIT_CHOICES.
        currency (str): The currency for the upload, chosen from
            CURRENCY_CHOICES.
        initial_data (dict): The initial data extracted from the uploaded file.
        data (dict): The validated data extracted from the uploaded file.
        data_hash (dict): The hash values of each row in the processed data.
        errors (dict): Any errors encountered during processing.
        is_used (bool): A flag indicating whether the upload has been used.
        is_confirmed (bool):  flag indicating whether the upload has been
            confirmed.
    """

    node = models.ForeignKey("supply_chains.Node", on_delete=models.CASCADE)
    template = models.ForeignKey(DataSheetTemplate,
                                 on_delete=models.PROTECT,
                                 related_name="uploads")
    file = models.FileField(upload_to=get_file_path, max_length=255)
    file_hash = models.CharField(max_length=500, null=True, blank=True)
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
    initial_data = fields.JSONField(default=dict, null=True, blank=True,
                                    encoder=DateTimeEncoder)
    data = fields.JSONField(default=dict, null=True, blank=True,
                            encoder=DateTimeEncoder)
    data_hash = fields.JSONField(default=dict, null=True, blank=True)
    errors = fields.JSONField(default=dict, null=True, blank=True)
    is_used = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"DataSheetUpload: {self.template.name} | {self.pk}"

    def save(self, *args, **kwargs):
        """Save the DataSheetUpload instance.

        This method is overridden to customize the save behavior of the
        DataSheetUpload model. It performs additional operations before saving
        the model instance. It checks if the instance is new or existing,
        creates a file hash for the uploaded file, and converts the file data
        to a dictionary format. Then, it calls the super() method to save the
        instance.

        Args:
            *args: Additional positional arguments to pass to the save method.
            **kwargs: Additional keyword arguments to pass to the save method.
        """
        self.new_instance = not self.pk
        self.block_file_change()
        self.create_file_hash(self.file,
                              check_type=kwargs.pop("check_type", "is_used"))
        self.file_to_dict()
        self.update_template()
        super().save(*args, **kwargs)

    def create_file_hash(self, file, check_type="is_used"):
        """Create a hash for the uploaded file.

        This method creates a hash for the uploaded file. It checks if a file
        exists, calculates the hash using the 'hash_file' function, and
        verifies that no other uploads with the same file hash and node exist.
        If a file hash already exists for an active upload with the same node,
        an exception is raised.

        Args:
            file: The uploaded file.
            check_type: check duplicate with 'is_used' or 'is_confirmed.'

        Raises:
            Exception: If a file already exists with the same file hash and
            node.
        """
        if self.file:
            file_hash = hash_file(file)
            check = ({"is_confirmed": True}
                     if check_type == "is_confirmed"
                     else {"is_used": True})
            uploads = self.__class__.objects.filter(
                file_hash=file_hash, **check, node=self.node
            )
            if uploads.exists():
                raise ValidationError(f"File already"
                                      f" {check_type.split('_')[-1]}")
            self.file_hash = file_hash

    def file_to_dict(self):
        """Convert the uploaded file to a dictionary.

        This method converts the uploaded file to a dataframe and then converts
        the dataframe to a dictionary format.
        The supported file formats are CSV, Excel (XLSX), and JSON. The
        converted data is stored in the 'initial_data' attribute of the model
        instance.

        Raises:
            Exception: If an invalid file format or an unrecognized file
            extension is encountered.
        """
        if not self.file:
            self.initial_data = {}

        def format_file_df(f_df):
            """Format the file dataframe, set the header row and data row."""
            header_row = f_df.iloc[self.template.title_row]
            f_df = f_df.iloc[self.template.data_row :]  # noqa
            f_df = f_df.set_axis(header_row.str.strip(), axis=1)
            return f_df

        file = self.file._get_file()  # noqa
        if self.file.name.endswith(".csv"):
            df = pd.read_csv(file, header=None)
            df = format_file_df(df)
        elif self.file.name.endswith(".xlsx"):
            df = pd.read_excel(file, header=None)
            df = format_file_df(df)
        elif self.file.name.endswith(".json"):
            df = pd.read_json(file, orient="index")
        else:
            raise Exception(
                "Invalid file format. Unrecognized file " "extension."
            )

        df.replace("\xa0", np.nan, inplace=True)
        df.dropna(how="all", inplace=True)
        df.fillna("", inplace=True)
        self.initial_data = df.to_dict(orient="index")

    def block_file_change(self):
        """Block file change if file already exists."""
        if not self.new_instance:
            old = self.__class__.objects.get(pk=self.pk)
            if old.file != self.file:
                raise Exception("Cannot change file")

    def update_template(self):
        """
        Update the data sheet template with product, unit, and currency
        information.
        """
        if self.template.is_system_template:
            return
        self.template.product = self.product
        self.template.unit = self.unit
        self.template.currency = self.currency
        self.template.save()


class DataSheetUploadSummary(AbstractBaseModel):
    """Model representing the summary of a data sheet upload.

    This model contains counters that track the number of farmers to add,
    farmers added, farmers to update, farmers updated, transactions to add,
    and transactions added for a specific data sheet upload.

    Attributes:
        upload (DataSheetUpload): The related data sheet upload.
        farmers_to_add (int): The number of farmers to add.
        farmers_added (int): The number of farmers added.
        farmers_to_update (int): The number of farmers to update.
        farmers_updated (int): The number of farmers updated.
        transactions_to_add (int): The number of transactions to add.
        transactions_added (int): The number of transactions added.
        total_price (int): The total price of all transactions.
        total_quantity (int): The total quantity of all transactions.
        average_quantity (int): The average quantity of all transactions.
        highest_quantity (int): The highest quantity of all transactions.
        lowest_quantity (int): The lowest quantity of all transactions.
    """

    upload = models.OneToOneField(
        DataSheetUpload, on_delete=models.CASCADE, related_name="summary"
    )
    farmers_to_add = models.IntegerField(default=0)
    farmers_added = models.IntegerField(default=0)
    farmers_to_update = models.IntegerField(default=0)
    farmers_updated = models.IntegerField(default=0)
    transactions_to_add = models.IntegerField(default=0)
    transactions_added = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0)
    total_quantity = models.IntegerField(default=0)
    average_quantity = models.IntegerField(default=0)
    highest_quantity = models.IntegerField(default=0)
    lowest_quantity = models.IntegerField(default=0)

    def __str__(self):
        return (
            f"DataSheetUploadSummary: "
            f"{self.upload.template.name} | {self.pk}"
        )
