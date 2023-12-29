"""Serializers of claims for consumer interface APIs.

DRF serializer is avoided to reduce page load time since, since gude
amount of data needs to be serialized.
"""
from v2.supply_chains.serializers import functions as ci_node_serializers


def serialize_field(field):
    """To perform function serialize_field."""
    data = {
        "field_id": field.idencode,
        "options": field.get_options(),
        "type": field.type,
        "title": field.title,
        "description": field.description,
        "multiple_options": field.multiple_options,
    }
    return data


def serialize_field_response(field_response):
    """To perform function serialize_field_response."""
    data = serialize_field(field_response.field)
    data["file"] = field_response.file_url
    data["response"] = field_response.response
    data["added_by"] = ci_node_serializers.serialize_node_basic(
        field_response.added_by
    )
    return data


def serialize_criterion(criterion):
    """To perform function serialize_criterion."""
    data = {
        "criterion_id": criterion.idencode,
        "name": criterion.name,
        "description": criterion.description,
        "verification_type": criterion.verification_type,
        "context": criterion.context,
        "method": criterion.method,
    }
    return data


def serialize_batch_criterion(batch_criterion):
    """To perform function serialize_batch_criterion."""
    data = serialize_criterion(batch_criterion.criterion)
    data["evidences"] = batch_criterion.evidence
    data["field_responses"] = [
        serialize_field_response(resp)
        for resp in batch_criterion.field_responses.all()
    ]
    return data


def serialize_claim(claim):
    """To perform function serialize_claim."""
    data = {
        "claim_id": claim.idencode,
        "name": claim.name,
        "description_basic": claim.description_basic,
        "description_full": claim.description_full,
        "image": claim.image.url if claim.image else "",
    }
    return data


def serialize_batch_claim(batch_claim):
    """To perform function serialize_batch_claim."""
    claim_data = serialize_claim(batch_claim.claim)
    bc_data = {}
    bc_data["attached_from"] = batch_claim.attached_from
    bc_data["status"] = batch_claim.status
    bc_data["blockchain_address"] = batch_claim.blockchain_address
    bc_data["criteria"] = [
        serialize_batch_criterion(crit) for crit in batch_claim.criteria.all()
    ]
    bc_data = {**bc_data, **claim_data}
    evidences = {}
    context = []
    method = 0
    for criterion in bc_data["criteria"]:
        method = criterion["method"]
        if criterion["context"]:
            context.append(criterion["context"])
        for resp in criterion["field_responses"]:
            resp_data = {
                "field_id": resp["field_id"],
                "title": resp["title"],
                "resp": resp["response"],
                "file": resp["file"],
                "type": resp["type"],
            }
            if resp["added_by"]["id"] not in evidences:
                evidences[resp["added_by"]["id"]] = {
                    "added_by": resp["added_by"],
                    "data": [resp_data],
                }
            else:
                evidences[resp["added_by"]["id"]]["data"].append(resp_data)
    claim_info = {
        "claim_id": bc_data["claim_id"],
        "name": bc_data["name"],
        "description_basic": bc_data["description_basic"],
        "description_full": bc_data["description_full"],
        "status": bc_data["status"],
        "blockchain_address": bc_data["blockchain_address"],
        "attached_from": bc_data["attached_from"],
        "context": context,
        "evidences": list(evidences.values()),
        "method": method,
        "primary_claim": False,
        "image": bc_data["image"],
    }
    return claim_info
