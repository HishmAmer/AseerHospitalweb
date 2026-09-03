from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """يستبدل حقل الجنسية النصي بالمفتاح الخارجي الذي عبّأته الهجرة السابقة.

    فُصلت عن 0020 عمداً: الحذف وإعادة التسمية يجب أن يجريا بعد نقل كل القيم،
    فلو فشل النقل توقّفت الترحيلات والحقل النصي ما يزال سليماً.
    """

    dependencies = [
        ('employees', '0020_nationality_table'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='nationality',
        ),
        migrations.RenameField(
            model_name='employee',
            old_name='nationality_ref',
            new_name='nationality',
        ),
        migrations.AlterField(
            model_name='employee',
            name='nationality',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                to='employees.nationality', verbose_name='الجنسية',
            ),
        ),
    ]
