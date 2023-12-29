"""This script it created to update the registration id of the farmer from CSV
file.

Farmer is fetch using the first and last name and the id is update.
before updating, the id is cleaned to and int value
Ref: Confluence docs for details.
upload the csv file to drive and share the permission to anyone with a link
can view and paste link to CSV_URL
"""
import re
from difflib import SequenceMatcher

import pandas as pd
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.transactions.models import ExternalTransaction

CSV_URL = (
    "https://drive.google.com/file/d/1WSQ6Bt7aTuIHzO7J5v33H0lu1hyPWLB0/"
    "view?usp=sharing "
)


def convert_reg_to_int(reg):
    """To perform function convert_reg_to_int."""
    return int(re.findall(r"\d+", reg)[0])


def clean_reg(reg):
    """To perform function clean_reg."""
    number = convert_reg_to_int(reg)
    reg = reg.replace(str(number), "")
    reg = reg.replace(" ", "").replace("-", "").replace("0", "")
    return f"{reg}{number}"


def similar(a, b):
    """To perform function similar."""
    return SequenceMatcher(None, a, b).ratio()


node = Node.objects.get(id=3181)
farmers = Farmer.objects.filter(node_ptr__in=node.get_suppliers())

path = (
    "https://drive.google.com/uc?export=download&id=" + CSV_URL.split("/")[-2]
)
df = pd.read_csv(path)

for row in df.itertuples():
    df.at[row[0], "FARMER'S NAME"] = row[2].title().strip()
    df.at[row[0], "Unnamed: 2"] = row[3].title().strip()
    df.at[row[0], "FARMER'S CODE"] = clean_reg(row[4])

issue_items = []
for row in df.itertuples():
    try:
        obj = farmers.get(
            first_name=row[2],
            last_name=row[3],
            identification_no=(row[4]),
            city=row[6].strip(),
            street=row[7].strip(),
        )
        farmers = farmers.exclude(id=obj.id)
        continue
    except Exception:
        issue_items.append(list(row))
        # print(row[2], row[3], row[4])

for row in issue_items:
    try:
        same_id_far = farmers.get(identification_no=str(row[4]))
    except Exception:
        continue
    db_str = (
        f"{same_id_far.first_name}{same_id_far.last_name}".lower().replace(
            " ", ""
        )
    )
    sheet_str = f"{row[2]}{row[3]}".lower().replace(" ", "")
    ratio = similar(db_str, sheet_str)
    print(
        ratio,
        db_str,
        sheet_str,
        same_id_far.id,
        ", db city:",
        same_id_far.city,
        ", sheet city:",
        row[6],
        ", db street:",
        same_id_far.street,
        ", sheet street:",
        row[7],
    )
    print(ExternalTransaction.objects.filter(source=same_id_far))
    print(
        ratio,
        db_str,
        sheet_str,
        same_id_far.id,
        ", db city:",
        same_id_far.city,
        ", sheet city:",
        row[6],
        ", db street:",
        same_id_far.street,
        ", sheet street:",
        row[7],
    )
    if same_id_far.city.strip() == row[6].strip() and ratio >= 0.9:
        print(ratio, row, same_id_far.id)
    print(
        ratio,
        db_str,
        sheet_str,
        same_id_far.id,
        ", db city:",
        same_id_far.city,
        ", sheet city:",
        row[6],
        ", db street:",
        same_id_far.street,
        ", sheet street:",
        row[7],
    )
    if ratio >= 0.9:
        print(ratio, row, db_str, same_id_far.id)
    if db_str == sheet_str:
        print(row[2], row[3], same_id_far)

for row in issue_items:
    obj = farmers.filter(first_name=row[2], last_name=row[3])
    for f in obj:
        print(row[6], f.city, f.city == row[6].strip())
        print(row, ":", [f.city for f in obj])

farm = None
for row in issue_items:
    try:
        farm = farmers.get(
            first_name=row[2], last_name=row[3], city=row[6].strip()
        )
    except Exception:
        continue
    print(farm.identification_no, row[4])
    farm.identification_no = row[4]
    farm.save()
obj = farmers.get(
    first_name=row[2], last_name=row[3], identification_no=str(row[4])
)

issue_items = []
obj = None
node = None
for row in df.itertuples():
    try:
        obj = farmers.get(
            first_name=row[2],
            last_name=row[3],
            city=row[6].strip(),
            street=row[7].strip(),
        )
    except Exception:
        issue_items.append(list(row))
        continue
    if obj.identification_no != str(row[4]):
        print(obj, obj.identification_no, str(row[4]))
        node = Node.objects.get(id=obj.id)
        node.identification_no = str(row[4])
        node.save()
        print("after id", farmers.get(id=obj.id).identification_no)

node = Node.objects.get(id=3181)
for row in issue_items:
    objs = farmers.filter(identification_no=str(row[4]))
    print(row, ":", objs)

for row in issue_items:
    try:
        obj = farmers.filter(
            first_name=row[2], last_name=row[3], city=row[6].strip()
        )
        print(obj, row)
    except Exception:
        continue

# for row in df.itertuples():
#     try:
#         obj = farmers.get(identification_no=(row[4]))
#         if obj.identification_no != clean_reg_new(row[4]):
#             print(obj.identification_no, ":", clean_reg_new(row[4]))

#     except Exception:
#         continue

for row in issue_items:
    print(farmers.filter(identification_no=row[4]))
