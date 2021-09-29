# -*- coding: utf-8 -*-
# Copyright 2016 Vauxoo

{
    'name': 'Costa Rica eInvoicing - PoS Base',
    'summary': """This module prepares odoo for eInvoicing services in Costa
    Rica in the Point of Sale.""",
    'version': '12.0.0.0.1',
    'category': 'Localization',
    'author': 'Vauxoo',
    'license': 'Other proprietary',
    'sequence': 10,
    'application': False,
    'installable': True,
    'auto_install': False,
    'depends': [
        'l10n_cr_edi',
        'point_of_sale'
    ],
    'data': [
        'views/templates.xml',
    ],
    'qweb': ['static/src/xml/pos.xml'],
    'external_dependencies': {
        'python': ['phonenumbers']
    },
}
