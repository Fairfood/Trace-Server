from collections import defaultdict

import pandas as pd
from pandera.errors import SchemaErrors
from rest_framework.exceptions import ValidationError


class SchemaFormattedErrors:
    """Schema for formatted error response."""

    errors = None
    data = None

    def __init__(self, exception: SchemaErrors):
        failure_cases = exception.failure_cases
        data = exception.data

        failure_indices = failure_cases["index"].dropna().astype(int)
        failure_indices_unique = failure_indices.drop_duplicates()

        self.errors = (
            data.loc[failure_indices_unique].fillna(
                "").replace({pd.NaT: None}).to_dict(
                orient="index")
        )

        dataframe_check_list = defaultdict(list)
        invalid_or_missing_columns = []

        for case in failure_cases.values:
            case_index = case[-1]
            case_column = case[1]
            case_context = case[0]
            case_check = case[2]
            case_failure = case[-2]

            if case_index is None:
                invalid_or_missing_columns.append(
                    (case_failure, "Missing")
                    if case_check == "column_in_dataframe"
                    else (case_column, f"Not expecting {case_failure}"))
                continue

            # create errors key if it doesn't exist
            if "errors" not in self.errors[case_index]:
                self.errors[case_index]["errors"] = []

            # replace column name from check if DataFrameSchema
            if case_context == "DataFrameSchema":
                if "_check" in case_check:
                    # DataFrameSchema checks will show for all columns. so
                    # we need to check if the check has already been added to
                    # the list.
                    if (case_index in dataframe_check_list
                            and case_check in dataframe_check_list[
                                case_index]):
                        continue
                    dataframe_check_list[case_index].append(case_check)
                    case_column = case_check.split('_check')[0]
                if case_check == "column_in_dataframe":
                    case_column = case_failure

            self.errors[case_index]["errors"].append({
                "key": case_column,
                "reason": f"Invalid {case_column.title()}",
            })
        if invalid_or_missing_columns:
            raise ValidationError(
                detail=dict(invalid_or_missing_columns),
            )
        self.data = (
            exception.data.drop(
                failure_indices).fillna("").replace({pd.NaT: None}).to_dict(
                orient="index")
        )
