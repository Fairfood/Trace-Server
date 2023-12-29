"""Script to push app txn data into google sheet."""
import pandas as pd
import pygsheets
from django.db.models import Sum
from v2.projects.models import Payment
from v2.supply_chains.models.profile import Farmer
from v2.transactions.models import ExternalTransaction

VERIFICATION_METHOD_MANUAL = 1
VERIFICATION_METHOD_CARD = 2

G_KEY = "/etc/secret/fairtrace_v2/gsheet.json"
SHEET_NAME = "Harvest app supplier trasactions to date"

HEADS_TXN = [
    "Sender",
    "Date",
    "Product",
    "Quantity(KG)",
    "Base price paid(IDR)",
    "Data Premium(IDR)",
    "Quality Premium(IDR)",
    "Total amount paid(IDR)",
    "Verification",
    "Creator",
    "Invoice",
]
HEADS_FARMER = ["No", "Created on", "Farmer Name", "Creator", "Mobile"]
HEADS_STATS = [
    "Date",
    "Toko new txns",
    "Multi new txn",
    "Toko all txns",
    "Multi all txns",
]

STATS_SHEET_INDEX = 0

NODES = [
    {
        "name": "Tokonaga",
        "id": 1432,
        "qp_id": 4,
        "dp_id": 2,
        "collectors": [238, 237, 227, 224],
        "sheet_index": 1,
        "txn_sheet_starting": (2, 1),
        "farmer_sheet_starting": (2, 13),
    },
    {
        "name": "Multi",
        "id": 2144,
        "qp_id": 3,
        "dp_id": 1,
        "collectors": [229, 230],
        "sheet_index": 2,
        "txn_sheet_starting": (2, 1),
        "farmer_sheet_starting": (2, 13),
    },
]


class HarvestDataWriter:
    """Stats to g sheet writer calls."""

    nodes = NODES
    sheet = None

    def __init__(self):
        """Initialize."""
        gc = pygsheets.authorize(service_file=G_KEY)
        self.sheet = gc.open(SHEET_NAME)

    @property
    def node_ids(self):
        """List of node ids."""
        return [node["id"] for node in self.nodes]

    @property
    def node_names(self):
        """List of node name."""
        return [node["name"] for node in self.nodes]

    def get_txn_list(self, node):
        """Generate the transaction details of the node."""
        data = []
        txns = ExternalTransaction.objects.filter(
            destination=node["id"]
        ).order_by("created_on")
        for txn in txns:
            q_prem = self.qs_sum(
                Payment.objects.filter(
                    premium=node["qp_id"], transaction=txn.id
                )
            )

            d_prem = self.qs_sum(
                Payment.objects.filter(
                    premium=node["dp_id"], transaction=txn.id
                )
            )

            mthd = "Receipt photo" if txn.verification_method == 1 else "Card"

            invoice = txn.invoice.url if txn.invoice else ""
            data.append(
                [
                    txn.source.full_name,
                    str(txn.created_on.date()),
                    txn.product.name,
                    float(txn.source_quantity),
                    txn.price,
                    d_prem,
                    q_prem,
                    txn.price + d_prem + q_prem,
                    mthd,
                    txn.creator.name,
                    invoice,
                ]
            )

        return data

    @staticmethod
    def qs_sum(qs, key="amount"):
        """Sum from query set."""
        total = qs.aggregate(total=Sum(key))["total"]
        if not total:
            total = 0.0
        return total

    @staticmethod
    def get_farmer_list(node):
        """Generate the farmer details."""
        data = []
        count = 1
        farmers = Farmer.objects.filter(
            creator__in=node["collectors"]
        ).order_by("created_on")
        for farmer in farmers:
            data.append(
                [
                    count,
                    str(farmer.created_on.date()),
                    farmer.full_name,
                    farmer.creator.name,
                    farmer.phone,
                ]
            )
            count += 1
        return data

    def get_txn_stats(self):
        """Get the transaction statistics."""
        data = {}
        txns = ExternalTransaction.objects.filter(
            destination__id__in=self.node_ids
        ).order_by("date")
        for txn in txns:
            if str(txn.date.date()) not in data:
                data[str(txn.date.date())] = dict(
                    (name, 0) for name in self.node_names
                )

            for node in self.nodes:
                if node["id"] == int(txn.destination.id):
                    node = node
                    break
            data[str(txn.date.date())][node["name"]] += 1

        return self.prep_stats(data)

    @staticmethod
    def prep_stats(data):
        """Prepare status format from data."""
        stats = []
        for date, values in data.items():
            row = [date]
            for node, count in values.items():
                row.append(count)
            stats.append(row)
        for stat in stats:
            index = stats.index(stat)
            stat_len = len(stat)
            for pos in range(1, len(stat)):
                if index == 0:
                    stat.append(stat[pos])
                else:
                    stat.append(
                        stat[pos] + stats[index - 1][stat_len + pos - 1]
                    )
        return stats

    def write_to_gsheet(self, data, book_index, starting, headings):
        """To write data into google sheet."""
        wks = self.sheet[book_index]
        if not data:
            print("no data to add")
        df = pd.DataFrame(data, columns=headings)
        wks.set_dataframe(df, starting)

    def write(self):
        """Function will push data into google sheet."""
        self.write_to_gsheet(self.get_txn_stats(), 0, (1, 9), HEADS_STATS)
        for node in self.nodes:
            self.write_to_gsheet(
                self.get_txn_list(node),
                node["sheet_index"],
                node["txn_sheet_starting"],
                HEADS_TXN,
            )
            self.write_to_gsheet(
                self.get_farmer_list(node),
                node["sheet_index"],
                node["farmer_sheet_starting"],
                HEADS_FARMER,
            )


def export_txn():
    """Main."""
    writer = HarvestDataWriter()
    writer.write()


# if __name__ == "__main__":
#     main()
