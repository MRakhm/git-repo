# Generated by Django 4.2.2 on 2024-04-28 19:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_cartorderproducts_product"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cartorderproducts",
            name="product",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.product",
            ),
        ),
    ]
