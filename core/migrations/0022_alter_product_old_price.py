# Generated by Django 4.2.2 on 2024-04-28 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_cartorder_cheque_picture_cartorder_comments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="old_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=99999999999999, null=True
            ),
        ),
    ]
