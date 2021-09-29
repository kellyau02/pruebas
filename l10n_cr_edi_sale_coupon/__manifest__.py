# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).
{
    'name': 'CR EDI sale coupon',
    'summary': '''
    Allow generate EDI documents with sale coupons
    ''',
    'author': 'Vauxoo',
    'website': 'https://www.vauxoo.com',
    'license': 'LGPL-3',
    'category': 'Installer',
    'version': '14.0.1.0.0',
    'depends': [
        'l10n_cr_edi_discount',
        'sale_coupon',
    ],
    'test': [
    ],
    'data': [
        'views/res_config_settings.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}
