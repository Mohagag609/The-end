#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create default currency if not exists
python manage.py shell << END
from core.models import Currency
if not Currency.objects.filter(is_default=True).exists():
    Currency.objects.create(
        code='EGP',
        name='جنيه مصري',
        symbol='ج.م',
        is_default=True
    )
    print('Default currency created')
END