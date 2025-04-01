from common.exceptions import AccessForbidden, UnauthorizedAccess


def check_node(request, node):
    """To perform function check_node."""
    buyers = node.get_buyers().values_list(
        "company__make_farmers_private", flat=True)
    # private farmers need extra check
    if any(buyers):
        dob = request.query_params.get("dob")
        if not dob:
            raise UnauthorizedAccess("Date of birth is required",
                             code="missing_dob")
        if not node.farmer.dob:
            raise AccessForbidden("Date of birth not set", code="missing_dob")
        if node.farmer.dob.strftime("%Y-%m-%d") != dob:
            raise AccessForbidden("Incorrect dob", code="incorrect_dob")