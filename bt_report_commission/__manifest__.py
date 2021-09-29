{
    "name": "Comisiones",
    "summary": "Cálculo de las comisiones",
    "category": "account",
    "version": "21.09.22",
    "sequence": 1,
    "author": "Boostech CR",
    "license": "",
    "website": "",
    "depends": [
        'account_accountant',
        'stock'
    ],
    "data": [
        'views/view_bt_commission.xml',
        'views/view_bt_commission_category.xml',
        'views/view_bt_commission_profile.xml',
        'views/view_bt_commission_job.xml',
        'report/view_bt_account_line_report.xml',
        'wizards/wizard_bt_commission.xml',
        'security/ir.model.access.csv',
        'views/menu.xml'

    ],
    "images": ['static/description/banner.png'],
    "application": False,
    "installable": True,
    "auto_install": False,
}