"""custom used Serializers are declared here."""
from collections import defaultdict

from django.contrib.auth import get_user_model

from common.drf_custom import fields as custom_fields
from common.drf_custom.fields import RelatedIdencodeField
from rest_framework import serializers


class CurrentUserDefault:
    def set_context(self, serializer_field):
        request = serializer_field.context.get('request')
        self.user = request.user if request else None

    def __call__(self):
        return self.user

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class IdencodeModelSerializer(serializers.ModelSerializer):
    """Common serializer for Idencode."""

    id = custom_fields.IdencodeField(read_only=True)
    creator = RelatedIdencodeField(default=CurrentUserDefault(),
                                   queryset=get_user_model().objects.all())
    updater = RelatedIdencodeField(default=CurrentUserDefault(),
                                   queryset=get_user_model().objects.all())
    serializer_related_field = RelatedIdencodeField


class CircularSerializer(serializers.Serializer):
    """This is a helper class to avoid circular imports.

     CircularSerializer(
        module='v2.supply_chains.serializers', -- package name
        serializer_class='node.CompanySerializer', -- file_name.class_name
        required=False)

    Imp: Only use in case of circular import issue.
    """

    serializer_class = None
    related_model = None
    module = None
    serializer = None
    kwargs = {}

    def __init__(self, **kwargs):
        assert "serializer_class" in kwargs, "serializer_class is required."
        assert "module" in kwargs, "module is required."

        # Attach serializer class and module with class.
        self.serializer_class = kwargs.pop("serializer_class")
        self.module = kwargs.pop("module")
        self.related_model = kwargs.pop("related_model", None)
        self.kwargs = kwargs
        super(CircularSerializer, self).__init__(kwargs)

    def to_representation(self, instance):
        """Representation data."""
        self.set_serializer()
        serializer = self.serializer(self.type_cast(instance), **self.kwargs)
        return serializer.data

    def to_internal_value(self, data):
        """Validate the serializer with data and returns it."""
        self.set_serializer()
        kwargs = self.kwargs
        kwargs["write_only"] = True
        serializer = self.serializer(data=data, **kwargs)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def update(self, instance, validated_data):
        """Override the default update."""
        return self.serializer(**self.kwargs).update(
            self.type_cast(instance), validated_data
        )

    def create(self, validated_data):
        """Override the default create."""
        return self.serializer(**self.kwargs).create(validated_data)

    def set_serializer(self):
        """Serializer class name to class conversion."""
        if not self.serializer:
            import sys

            # Get module
            module = sys.modules[self.module]
            serializer_class = self.serializer_class
            klass_name_list = serializer_class.split(".")

            # if class name is not direct, need to update module to get class
            if len(klass_name_list) > 1:
                module = getattr(module, klass_name_list[0])
                serializer_class = klass_name_list[1]
            self.serializer = getattr(module, serializer_class)
        return self.serializer

    def type_cast(self, instance):
        """Helps to convert between ORM inherited models."""
        if not self.related_model:
            return instance

        # Convert only if related_model is available.
        try:
            return self.related_model.objects.get(pk=instance.id)
        except self.related_model.DoesNotExist:
            return instance


class DynamicModelSerializer(IdencodeModelSerializer):
    """A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.

    * All serializers should inherit this class.
    * To initialize:
        - InheritedDynamicSerializer(
            fields=('id', 'name'),
            include_nested=('related_field.name', 'related_field.id')
            )
            --------or-------
        - InheritedDynamicSerializer(
            exclude_fields=('id', 'name'),
            exclude_nested=('related_field.name', 'related_field.id')
            )
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        exclude_fields = kwargs.pop("exclude_fields", None)
        exclude_nested = kwargs.pop("exclude_nested", None)
        include_nested = kwargs.pop("include_nested", None)
        optimize = kwargs.pop("optimize", False)

        # Check field combinations.
        assert not (fields and exclude_fields), (
            "Cannot use fields and " "exclude_fields together"
        )
        assert not (exclude_nested and include_nested), (
            "Cannot use " "exclude_nested and " "nested together"
        )
        # Instantiate the superclass normally
        super(DynamicModelSerializer, self).__init__(*args, **kwargs)

        if include_nested:
            self.include_nested_fields(include_nested)
        if exclude_nested:
            self.exclude_nested_fields(exclude_nested)
        if fields:
            self.include_direct_fields(fields)
        if exclude_fields:
            self.exclude_direct_fields(exclude_fields)

        if optimize:
            # TODO: Optimize with select_related and prefetch_related fields.
            pass

    def find_nth_serializer(self, first_depth, nested_fields):
        """To find the last nested serializer."""
        last_serializer = self.fields.get(first_depth)
        for _field in nested_fields:
            last_serializer = last_serializer.fields.get(_field)
        return last_serializer

    def include_nested_fields(self, include_nested):
        """To include the nested fields, dynamically modifying nested
        serializer fields."""
        serializer_list = defaultdict(list)

        # Map fields and their serializers.
        for items in include_nested:
            nested_fields = items.split(".")

            # The starting field
            first_depth = nested_fields.pop(0)

            nth_serializer = self.find_nth_serializer(
                first_depth, nested_fields.copy()
            )

            # The nth field
            nth_depth = nested_fields.pop(-1)
            serializer_list[nth_serializer].append(nth_depth)

        # Loop through all serializers and remove the excess fields
        for serializer, field_list in serializer_list.items():
            if serializer.fields:
                all_fields = set(serializer.fields.keys())
                inc_fields = set(field_list)
                x_fields = all_fields - inc_fields
                for field_name in x_fields:
                    serializer.fields.pop(field_name)

    def exclude_nested_fields(self, exclude_nested):
        """To exclude the nested fields,dynamically modifying nested serializer
        fields."""
        for items in exclude_nested:
            nested_fields = items.split(".")

            # The starting field.
            first_depth = nested_fields.pop(0)

            # The nth field or the excluding field.
            x_field = nested_fields.pop(-1)
            nth_serializer = self.find_nth_serializer(
                first_depth, nested_fields.copy()
            )
            if nth_serializer.fields:
                nth_serializer.fields.pop(x_field)

    def include_direct_fields(self, fields):
        """To include the direct fields,dynamically modifying serializer
        fields."""
        allowed = set(fields)
        existing = set(self.fields.keys())

        # Drop any fields that are not specified in the `fields` argument.
        for field_name in existing - allowed:
            self.fields.pop(field_name)

    def exclude_direct_fields(self, exclude_fields):
        """To exclude the direct fields."""
        exclude = set(exclude_fields)

        # Drop specific fields
        for field_name in exclude:
            self.fields.pop(field_name)
