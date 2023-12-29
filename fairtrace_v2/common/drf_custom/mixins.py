"""Custom mixing."""
from common.library import _pop_out_from_dictionary


class WriteOnceMixin:
    """Adds support for write once fields to Serializers.

    To use it, specify a list of fields as `write_once_fields` on the
    serialize r's Meta:
    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        write_once_fields = ('collection', )
    ```

    Now the fields in `write_once_fields` can be set during POST (create),
    but cannot be changed afterwards via PUT or PATCH (update).
    """

    def get_extra_kwargs(self):
        """Popping out extra fields."""
        extra_kwargs = (
            super().get_extra_kwargs()
        )  # pytype: disable=attribute-error

        if not (self.instance is None):
            args = self._set_write_once_fields(
                extra_kwargs
            )  # pytype: disable=attribute-error
            return args

        return extra_kwargs

    def _set_write_once_fields(self, extra_kwargs):
        """Set all fields in `Meta.write_once_fields` to read_only."""
        made_mutable = False
        try:
            _mutable = self._kwargs["data"]._mutable
            self._kwargs["data"]._mutable = True
            made_mutable = True
        except Exception:
            pass

        try:
            _pop_out_from_dictionary(self._kwargs["data"], ["creator"])
        except Exception:
            pass
        write_once_fields = getattr(self.Meta, "write_once_fields", None)
        if not write_once_fields:
            return extra_kwargs

        if not isinstance(write_once_fields, (list, tuple)):
            raise TypeError(
                "The `write_once_fields` option must be a list or tuple."
                " Got {}.".format(type(write_once_fields).__name__)
            )
        try:
            _pop_out_from_dictionary(self._kwargs["data"], write_once_fields)
        except Exception as e:
            print(e)
            pass
        if made_mutable:
            self._kwargs["data"]._mutable = _mutable
        return extra_kwargs


def inject_node(request, **kwargs) -> None:
    """Inject the current node.

    This method inserts the current node into the request data.

    Args:
        request (Request): The request object.
        **kwargs: Additional keyword arguments.
    """
    node = kwargs.get("node")

    # Only proceed if node is available.
    if not node:
        return None
    set_mutable = False

    # Check for mutable flag present for request data.
    if hasattr(request.data, "_mutable"):
        set_mutable = True

    if set_mutable:
        mutable = request.data._mutable  # noqa
        # set data as mutable
        request.data._mutable = True
        request.data["node"] = node.idencode
        # restore to original
        request.data._mutable = mutable
    else:
        request.data["node"] = node.idencode
