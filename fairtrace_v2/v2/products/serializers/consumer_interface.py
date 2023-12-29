"""Serializers for products related APIs."""
from common.drf_custom import fields as custom_fields
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from v2.products.models import Product

product_data_cache = {}


class CIProductSerializer(serializers.Serializer):
    """Product serializer."""

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField(read_only=True)
    theme = None

    class Meta:
        model = Product
        fields = ("id", "name", "description", "image")

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        self.theme = kwargs.pop("theme", None)
        super(CIProductSerializer, self).__init__(*args, **kwargs)

    def to_representation(self, instance):
        """To perform function to_representation."""
        key = (instance, self.__class__, self.theme)
        if key in product_data_cache:
            return product_data_cache[key]

        data = super(CIProductSerializer, self).to_representation(instance)
        data["location"] = ""

        if self.theme:
            try:
                product = self.theme.products.get(product=instance)
                data["name"] = product.name
                data["image"] = product.image_url
                data["description"] = product.description
                data["location"] = product.location
            except Exception as e:
                print(e)
                pass
        product_data_cache[key] = data
        return data


def serialize_product(product, theme=None):
    """To perform function serialize_product."""
    # common_lib._time_since(intend=2, stage="[serialize_product] start")
    # global product_data_cache
    # key = ('serialize_product', product, theme)
    # if key in product_data_cache:
    #     return product_data_cache[key]
    # common_lib._time_since(intend=2, stage="[serialize_product] mid")
    data = {
        "id": product.idencode,
        "name": product.name,
        "description": "",
        "location": "",
        "image": "",
        "incoming": False,
        "outgoing": False,
        "processed": False,
    }
    if theme:
        try:
            product = theme.products.get(product=product)
            data["name"] = product.name
            data["image"] = product.image_url
            data["description"] = product.description
            data["location"] = product.location
        except ObjectDoesNotExist:
            data["name"] = product.name
            data["image"] = product.image.url if product.image else ""
            data["description"] = product.description
    # product_data_cache[key] = data
    # common_lib._time_since(intend=2, stage="[serialize_product] end")
    return data
