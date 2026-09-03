from django.db import migrations, models
import django.db.models.deletion


# القائمة كما كانت مضمَّنة في النموذج قبل تحويلها إلى جدول يُدار من الإعدادات.
# مثبَّتة هنا نصاً بقصد: الهجرة يجب أن تُنتج النتيجة نفسها مهما تغيّرت القوائم
# في الشيفرة لاحقاً. الترتيب هو ترتيب القائمة الأصلية (حسب المنطقة، «سعودي»
# أولاً) ويُحفظ في display_order حتى تبقى القائمة مألوفة لمن يُدخل البيانات.
SEED_NATIONALITIES = [
    'سعودي', 'إماراتي', 'كويتي', 'قطري', 'عماني', 'بحريني', 'مصري', 'يمني', 'سوداني',
    'أردني', 'سوري', 'فلسطيني', 'لبناني', 'عراقي', 'تونسي', 'مغربي', 'جزائري', 'ليبي',
    'صومالي', 'موريتاني', 'جيبوتي', 'قمري', 'هندي', 'فلبيني', 'باكستاني', 'بنغلاديشي',
    'إندونيسي', 'سريلانكي', 'نيبالي', 'ماليزي', 'أفغاني', 'ميانماري', 'صيني', 'ياباني',
    'كوري', 'كوري شمالي', 'تايلاندي', 'فيتنامي', 'سنغافوري', 'تركي', 'إيراني', 'أوزبكي',
    'طاجيكي', 'كازاخي', 'قيرغيزي', 'تركماني', 'أذربيجاني', 'أرميني', 'جورجي', 'منغولي',
    'كمبودي', 'لاوسي', 'بروناوي', 'تيموري', 'مالديفي', 'بوتاني', 'قبرصي', 'جنوب أفريقي',
    'نيجيري', 'كينى', 'إثيوبي', 'إريتري', 'تشادي', 'غاني', 'أوغندي', 'مالي', 'سنغالي',
    'كوت ديفوار', 'كاميروني', 'رواندي', 'جنوب سوداني', 'تنزاني', 'زامبي', 'زيمبابوي',
    'موزمبيقي', 'أنغولي', 'ناميبي', 'بوتسواني', 'ملاوي', 'بوروندي', 'كونغولي',
    'كونغولي برازافيل', 'غابوني', 'غيني', 'بيساوي', 'غيني استوائي', 'بنيني', 'توغولي',
    'بوركيني', 'نيجري', 'سيراليوني', 'ليبيري', 'غامبي', 'رأس أخضر', 'مدغشقري', 'موريشيوسي',
    'سيشلي', 'أفريقي وسطي', 'ليسوتي', 'إسواتيني', 'ساوتومي', 'بريطاني', 'فرنسي', 'ألماني',
    'إيطالي', 'إسباني', 'هولندي', 'سويدي', 'سويسري', 'نمساوي', 'بلجيكي', 'برتغالي',
    'دانماركي', 'نرويجي', 'فنلندي', 'بولندي', 'يوناني', 'روسي', 'أوكراني', 'بوسني',
    'ألباني', 'روماني', 'أيرلندي', 'آيسلندي', 'تشيكي', 'سلوفاكي', 'مجري', 'بلغاري', 'صربي',
    'كرواتي', 'سلوفيني', 'مقدوني', 'جبل أسود', 'كوسوفي', 'ليتواني', 'لاتفي', 'إستوني',
    'بيلاروسي', 'مولدوفي', 'مالطي', 'لوكسمبورغي', 'ليختنشتايني', 'موناكي', 'أندوري',
    'سان ماريني', 'أمريكي', 'كندي', 'برازيلي', 'أرجنتيني', 'فنزويلي', 'مكسيكي', 'كولومبي',
    'كوبي', 'تشيلي', 'بيروفي', 'إكوادوري', 'بوليفي', 'أوروغواياني', 'باراغواياني', 'غوياني',
    'سورينامي', 'بنمي', 'كوستاريكي', 'نيكاراغوي', 'هندوراسي', 'سلفادوري', 'غواتيمالي',
    'بليزي', 'دومينيكاني', 'هايتي', 'جامايكي', 'ترينيدادي', 'بربادوسي', 'بهامي', 'أسترالي',
    'نيوزيلندي', 'بابوي', 'فيجي', 'ساموي', 'تونغي', 'فانواتي', 'سليماني', 'كيريباتي',
    'ميكرونيزي', 'بالاوي', 'ناوروي', 'توفالي', 'مارشالي', 'بدون جنسية', 'أخرى',
]


def seed_and_link(apps, schema_editor):
    Nationality = apps.get_model('employees', 'Nationality')
    Employee = apps.get_model('employees', 'Employee')

    for order, name in enumerate(SEED_NATIONALITIES, start=1):
        Nationality.objects.get_or_create(name=name, defaults={'display_order': order})

    # قيمة مخزَّنة خارج القائمة (كتابة مباشرة في قاعدة البيانات مثلاً) تُنشأ
    # جنسيةً جديدة بدل أن تُفقد. لا يضيع أي سجل في هذه الهجرة.
    existing = (
        Employee.objects.exclude(nationality__isnull=True)
        .exclude(nationality='')
        .values_list('nationality', flat=True)
        .distinct()
    )
    next_order = len(SEED_NATIONALITIES)
    for name in existing:
        if not Nationality.objects.filter(name=name).exists():
            next_order += 1
            Nationality.objects.create(name=name, display_order=next_order)

    by_name = {n.name: n.pk for n in Nationality.objects.all()}
    for name, pk in by_name.items():
        Employee.objects.filter(nationality=name).update(nationality_ref=pk)


def unlink(apps, schema_editor):
    """يعيد الاسم النصي إلى الحقل القديم قبل التراجع عن التحويل."""
    Employee = apps.get_model('employees', 'Employee')
    for employee in Employee.objects.select_related('nationality_ref'):
        employee.nationality = employee.nationality_ref.name if employee.nationality_ref else ''
        employee.save(update_fields=['nationality'])


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0019_merge_employee_type_and_classification'),
    ]

    operations = [
        migrations.CreateModel(
            name='Nationality',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='الجنسية')),
                ('display_order', models.PositiveIntegerField(default=0, verbose_name='ترتيب العرض')),
            ],
            options={
                'verbose_name': 'جنسية',
                'verbose_name_plural': 'الجنسيات',
                'ordering': ('display_order', 'name'),
            },
        ),
        migrations.AddField(
            model_name='employee',
            name='nationality_ref',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                to='employees.nationality', verbose_name='الجنسية',
            ),
        ),
        migrations.RunPython(seed_and_link, unlink),
    ]
