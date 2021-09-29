# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Odoo Costa Rican Localization QR Generator in Reports',
    'summary': '''
        Electronic einvoicing report + QR Code with summary about invoice information.
    ''',
    'author': 'Vauxoo',
    'website': 'https://www.vauxoo.com',
    'license': 'AGPL-3',
    'category': 'Localization',
    'version': '13.0.1.0.0',
    'depends': [
        'l10n_cr_edi',
    ],
    'test': [
    ],
    'data': [
        'views/account_invoice.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
