# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'EDI Documents for CR',
    'summary': '''
    Main module to allow create EDI documents for CR on Odoo
    ''',
    'author': 'Vauxoo',
    'website': 'https://www.vauxoo.com',
    'license': 'LGPL-3',
    'category': 'Installer',
    'version': '14.0.1.0.0',
    'depends': [
        'l10n_cr_edi',
        'l10n_edi_document',
    ],
    'test': [
    ],
    'data': [
        'data/data.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
