"""Serializers for products related APIs."""
from common.drf_custom import fields as custom_fields
from rest_framework import serializers

from common.drf_custom.serializers import DynamicModelSerializer
from v2.products import constants as prod_constants
from v2.products.models import Product
from v2.supply_chains.models import SupplyChain


class SupplyChainSerializer(serializers.ModelSerializer):
    """Serializer for SupplyChains."""

    id = custom_fields.IdencodeField()

    class Meta:
        """Meta Data."""

        model = SupplyChain
        fields = ("id", "name", "description", "image")


class ProductSerializer(DynamicModelSerializer):
    """Product serializer."""

    id = custom_fields.IdencodeField(read_only=True)
    user = custom_fields.KWArgsObjectField(write_only=True)
    node = custom_fields.KWArgsObjectField(write_only=True)
    supply_chain = custom_fields.IdencodeField(
        serializer=SupplyChainSerializer
    )

    class Meta:
        model = Product
        fields = ("id", "user", "node", "name", "supply_chain")

    def create(self, validated_data):
        """Create overridden."""
        user = validated_data.pop("user")
        validated_data["creator"] = user
        validated_data["updater"] = user
        validated_data["type"] = prod_constants.PRODUCT_TYPE_LOCAL

        node = validated_data.pop("node")
        existing_products = Product.objects.filter(
            name__iexact=validated_data["name"],
            supply_chain=validated_data["supply_chain"],
        )
        if existing_products:
            product = existing_products[0]
            if product.type == prod_constants.PRODUCT_TYPE_LOCAL:
                product.owners.add(node)
        else:
            product = super(ProductSerializer, self).create(validated_data)
            product.owners.add(node)
            product.create_token()
        return product


class BulkCreateProduct(serializers.Serializer):
    """Create Multiple products together."""

    supply_chain = custom_fields.IdencodeField(related_model=SupplyChain)
    products = serializers.ListField(child=serializers.CharField())

    def create(self, validated_data):
        """Create overridden."""
        products = []
        for name in validated_data["products"]:
            prod_serializer = ProductSerializer(
                context=self.context,
                data={
                    "name": name.strip(),
                    "supply_chain": validated_data["supply_chain"].idencode,
                },
            )
            if not prod_serializer.is_valid():
                raise serializers.ValidationError(prod_serializer.errors)
            product = prod_serializer.save()
            products.append(prod_serializer.to_representation(product))
        return products

    def to_representation(self, data):
        """Representing value."""
        return {"products": data}
