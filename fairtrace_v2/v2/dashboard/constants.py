import json
import os

from django.conf import settings

trabocca_theme_file = os.path.join(
    settings.BASE_DIR, "v2", "dashboard", "trabocca-theme.json"
)

with open(trabocca_theme_file, "r") as themefile:
    TRABOCCA_THEME = json.loads(themefile.read())

HALF_WIDTH_BANNER = 1
FULL_WIDTH_BANNER = 2
BANNER_WIDTH_CHOICES = [
    (HALF_WIDTH_BANNER, "Half width banner"),
    (FULL_WIDTH_BANNER, "Full width banner"),
]
