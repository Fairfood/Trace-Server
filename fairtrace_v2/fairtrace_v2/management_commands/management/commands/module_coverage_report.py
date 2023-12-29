import sys
from collections import defaultdict
from io import StringIO

import coverage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Generates a coverage report for the project.

    The coverage report includes information about the module coverage
    percentage and the percentage of missing lines. It groups the report by
    module name.

    Usage:
    python manage.py coverage_report
    """

    help = "Generate a coverage report"

    def handle(self, *args, **options):
        """Generate a coverage report."""

        # Create a coverage instance
        cov = coverage.Coverage()

        # Load coverage data from the .coverage file
        cov.load()

        # Redirect console output to a string
        report_buffer = StringIO()
        sys.stdout = report_buffer

        # Generate coverage report
        cov.report(include="v2/*", skip_covered=True)

        # Reset console output
        sys.stdout = sys.__stdout__

        # Get the captured report data as a string
        report_data = report_buffer.getvalue()

        # Split the report data into a list of lines
        report_to_list = report_data.split("\n")[2:-5]

        # Group the report data by module name
        grouped_report = defaultdict(list)

        # Get the max width of the module name for pretty printing.
        max_width = 0

        # Loop through the report lines to group them by module name.
        for line in report_to_list:
            # Get the module name from the line
            module_name = ".".join(line.split(" ")[0].split("/")[:2])
            percentage = line.split(" ")[-1].strip("%")
            grouped_report[module_name].append(int(percentage))

            # Get the max width of the module name
            if len(module_name) > max_width:
                max_width = len(module_name)

        # Print the report
        self.stdout.write(
            f"Module{(max_width - 1) * ' '}Coverage{10 * ' '}Missing"
        )
        self.stdout.write(f"------{max_width * '-'}------------------------")
        for module, percentages in grouped_report.items():
            avg_percentage = round(sum(percentages) / len(percentages), 0)
            self.stdout.write(
                f"{module}{(max_width + 5 - len(module)) * ' '}"
                f"{avg_percentage}%{13 * ' '}{100 - avg_percentage}%"
            )
