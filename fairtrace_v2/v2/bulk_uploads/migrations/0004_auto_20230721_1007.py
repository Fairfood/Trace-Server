# Generated by Django 2.2.6 on 2023-07-21 04:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_batch_external_source'),
        ('bulk_uploads', '0003_auto_20230717_1313'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasheettemplate',
            name='currency',
            field=models.CharField(blank=True, choices=[('USD', 'United States dollar'), ('EUR', 'EURO'), ('ETB', 'Ethiopian birr'), ('IDR', 'Indonesian rupiah'), ('GBP', 'British pound'), ('AED', 'United Arab Emirates dirham'), ('ALL', 'Albanian lek'), ('AMD', 'Armenian dram'), ('ANG', 'Netherlands Antillean guilder'), ('AOA', 'Angolan kwanza'), ('ARS', 'Argentine peso'), ('AUD', 'Australian dollar'), ('AWG', 'Aruban florin'), ('AZN', 'Azerbaijani manat'), ('BAM', 'Bosnia and Herzegovina convertible mark'), ('BBD', 'Barbadian dollar'), ('BDT', 'Bangladeshi taka'), ('BGN', 'Bulgarian lev'), ('BHD', 'Bahraini dinar'), ('BIF', 'Burundian franc'), ('BMD', 'Bermudian dollar'), ('BND', 'Brunei dollar'), ('BOB', 'Bolivian boliviano'), ('BRL', 'Brazilian real'), ('BSD', 'Bahamian dollar'), ('BTN', 'Bhutanese ngultrum'), ('BWP', 'Botswana pula'), ('BYN', 'Belarusian ruble'), ('BZD', 'Belize dollar'), ('CAD', 'Canadian dollar'), ('CDF', 'Congolese franc'), ('CHF', 'Swiss franc'), ('CLP', 'Chilean peso'), ('CNY', 'Chinese yuan'), ('COP', 'Colombian peso'), ('CRC', 'Costa Rican colón'), ('CUC', 'Cuban convertible peso'), ('CUP', 'Cuban peso'), ('CVE', 'Cape Verdean escudo'), ('CZK', 'Czech koruna'), ('DJF', 'Djiboutian franc'), ('DKK', 'Danish krone'), ('DOP', 'Dominican peso'), ('DZD', 'Algerian dinar'), ('EGP', 'Egyptian pound'), ('ERN', 'Eritrean nakfa'), ('JPY', 'Japanese yen'), ('FJD', 'Fijian dollar'), ('FKP', 'Falkland Islands pound'), ('GEL', 'Georgian lari'), ('GGP', 'Guernsey pound'), ('GHS', 'Ghanaian cedi'), ('GIP', 'Gibraltar pound'), ('GMD', 'Gambian dalasi'), ('GNF', 'Guinean franc'), ('GTQ', 'Guatemalan quetzal'), ('GYD', 'Guyanese dollar'), ('HKD', 'Hong Kong dollar'), ('HNL', 'Honduran lempira'), ('HRK', 'Croatian kuna'), ('HTG', 'Haitian gourde'), ('HUF', 'Hungarian forint'), ('AFN', 'Afghan afghani'), ('ILS', 'Israeli new shekel'), ('IMP', 'Manx pound'), ('INR', 'Indian rupee'), ('IQD', 'Iraqi dinar'), ('IRR', 'Iranian rial'), ('ISK', 'Icelandic króna'), ('JEP', 'Jersey pound'), ('JMD', 'Jamaican dollar'), ('JOD', 'Jordanian dinar'), ('KES', 'Kenyan shilling'), ('KGS', 'Kyrgyzstani som'), ('KHR', 'Cambodian riel'), ('KID', 'Kiribati dollar'), ('KMF', 'Comorian franc'), ('KPW', 'North Korean won'), ('KRW', 'South Korean won'), ('KWD', 'Kuwaiti dinar'), ('KYD', 'Cayman Islands dollar'), ('KZT', 'Kazakhstani tenge'), ('LAK', 'Lao kip'), ('LBP', 'Lebanese pound'), ('LKR', 'Sri Lankan rupee'), ('LRD', 'Liberian dollar'), ('LSL', 'Lesotho loti'), ('LYD', 'Libyan dinar'), ('MAD', 'Moroccan dirham'), ('MDL', 'Moldovan leu'), ('MGA', 'Malagasy ariary'), ('MKD', 'Macedonian denar'), ('MMK', 'Burmese kyat'), ('MNT', 'Mongolian tögrög'), ('MOP', 'Macanese pataca'), ('MRU', 'Mauritanian ouguiya'), ('MUR', 'Mauritian rupee'), ('MVR', 'Maldivian rufiyaa'), ('MWK', 'Malawian kwacha'), ('MXN', 'Mexican peso'), ('MYR', 'Malaysian ringgit'), ('MZN', 'Mozambican metical'), ('NAD', 'Namibian dollar'), ('NGN', 'Nigerian naira'), ('NIO', 'Nicaraguan córdoba'), ('NOK', 'Norwegian krone'), ('NPR', 'Nepalese rupee'), ('NZD', 'New Zealand dollar'), ('OMR', 'Omani rial'), ('PAB', 'Panamanian balboa'), ('PEN', 'Peruvian sol'), ('PGK', 'Papua New Guinean kina'), ('PHP', 'Philippine peso'), ('PKR', 'Pakistani rupee'), ('PLN', 'Polish złoty'), ('PRB', 'Transnistrian ruble'), ('PYG', 'Paraguayan guaraní'), ('QAR', 'Qatari riyal'), ('RON', 'Romanian leu'), ('RSD', 'Serbian dinar'), ('RUB', 'Russian ruble'), ('RWF', 'Rwandan franc'), ('SAR', 'Saudi riyal'), ('SEK', 'Swedish krona'), ('SGD', 'Singapore dollar'), ('SHP', 'Saint Helena pound'), ('SLL', 'Sierra Leonean leone'), ('SLS', 'Somaliland shilling'), ('SOS', 'Somali shilling'), ('SRD', 'Surinamese dollar'), ('SSP', 'South Sudanese pound'), ('STN', 'São Tomé and Príncipe dobra'), ('SYP', 'Syrian pound'), ('SZL', 'Swazi lilangeni'), ('THB', 'Thai baht'), ('TJS', 'Tajikistani somoni'), ('TMT', 'Turkmenistan manat'), ('TND', 'Tunisian dinar'), ('TOP', 'Tongan paʻanga'), ('TRY', 'Turkish lira'), ('TTD', 'Trinidad and Tobago dollar'), ('TVD', 'Tuvaluan dollar'), ('TWD', 'New Taiwan dollar'), ('TZS', 'Tanzanian shilling'), ('UAH', 'Ukrainian hryvnia'), ('UGX', 'Ugandan shilling'), ('UYU', 'Uruguayan peso'), ('UZS', 'Uzbekistani soʻm'), ('VES', 'Venezuelan bolívar soberano'), ('VND', 'Vietnamese đồng'), ('VUV', 'Vanuatu vatu'), ('WST', 'Samoan tālā'), ('XAF', 'Central African CFA franc'), ('XCD', 'Eastern Caribbean dollar'), ('XOF', 'West African CFA franc'), ('XPF', 'CFP franc'), ('ZAR', 'South African rand'), ('ZMW', 'Zambian kwacha'), ('ZWB', 'Zimbabwean bonds')], max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='datasheettemplate',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='datasheettemplate',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='products.Product'),
        ),
        migrations.AddField(
            model_name='datasheettemplate',
            name='unit',
            field=models.IntegerField(blank=True, choices=[(1, 'KG'), (2, 'Tonne')], default=1, null=True),
        ),
        migrations.AlterField(
            model_name='datasheetupload',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploads', to='bulk_uploads.DataSheetTemplate'),
        ),
    ]
