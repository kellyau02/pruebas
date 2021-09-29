# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Catalog of Products and Services Code',
    'summary': ' CABYS Product/Services code',
    'author': 'Vauxoo',
    'website': 'https://www.vauxoo.com',
    'license': 'LGPL-3',
    'category': 'Accounting',
    'version': '14.0.1.0.0',
    'depends': ['product', 'account'],
    'data': [
        'views/product_view.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
    'application': True,
}
