# https://documenter.getpostman.com/view/12758640/TVKA5KUT
# https://app.tilopay.com
# https://tilopay.com/cr/
{
    "name": "Payment methods - Tilopay",
    "summary": "Payment methods - Tilopay",
    "category": "Payment methods",
    "version": "21.09.20",
    "sequence": 0,
    "author": "Boostech CR",
    "license": "",
    "website": "",
    "depends": [
        'payment'
    ],
    "data": [
        'views/view_payment_tilopay_template.xml',
        'views/view_payment_tilopay.xml',
        'views/view_payment_transaction.xml',
        # 'views/view_payment_tilopay.xml',
        'data/payment_acquirer_data.xml'
    ],
    "images": ['static/description/icon.png'],
    # "application": False,
    "installable": True,
    "auto_install": False,
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
