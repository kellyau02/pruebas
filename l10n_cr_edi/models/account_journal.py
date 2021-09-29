# Copyright 2016 Vauxoo

from odoo import models, fields


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    l10n_cr_edi_document_type = fields.Selection(
        selection=[
            ('01', 'Electronic Invoice'),
            ('04', 'Electronic Ticket'),
            ('02', 'Electronic debit note'),
            ('08', 'Electronic Purchase Invoice'),
            ('09', 'Electronic invoice for export')
        ],
        string='eInvoice document type',
        help='eInvoice document type')

    # This is used to set the purchase tax condition
    l10n_cr_edi_tax_condition = fields.Selection(
        selection=[
            ('none', 'State not defined'),
            ('01', 'Genera crédito IVA'),
            ('02', 'Genera Crédito parcial del IVA'),
            ('03', 'Bienes de Capital'),
            ('04', 'Gasto corriente no genera crédito'),
            ('05', 'Proporcionalidad')
        ],
        string='eInvoice tax condition',
        help='eInvoice tax condition')

    l10n_cr_edi_location = fields.Integer(
        string='eInvoice location number',
        help='eInvoice location number')

    l10n_cr_edi_terminal = fields.Integer(
        string='eInvoice terminal number',
        help='eInvoice terminal number')
