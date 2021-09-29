# Copyright 2016 Vauxoo

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_cr_edi_code = fields.Selection(
        selection=[
            ('01', 'Impuesto al Valor Agregado'),
            ('02', 'Impuesto Selectivo de Consumo'),
            ('03', 'Impuesto Único a los combustibles'),
            ('04', 'Impuesto específico de Bebidas Alcohólicas'),
            ('05', 'Impuesto Específico sobre las bebidas envasadas sin '
             'contenido alcohólico y jabones de tocador'),
            ('06', 'Impuesto a los Productos de Tabaco'),
            ('07', 'IVA (cálculo especial)'),
            ('08', 'IVA Régimen de Bienes Usados (Factor)'),
            ('12', 'Impuesto Específico al Cemento'),
            ('98', 'Otros')
        ],
        string='CR eInvoicing code',
        help='CR eInvoicing code')

    l10n_cr_edi_iva_code = fields.Selection(
        selection=[
            ('01', 'Tarifa 0% (Exento)'),
            ('02', 'Tarifa reducida 1%'),
            ('03', 'Tarifa reducida 2%'),
            ('04', 'Tarifa reducida 4%'),
            ('05', 'Transitorio 0%'),
            ('06', 'Transitorio 4%'),
            ('07', 'Transitorio 8%'),
            ('08', 'Tarifa general 13%')
        ],
        string='CR eInvoicing rate tax IVA',
        help='CR eInvoicing rate tax IVA')

    l10n_cr_edi_tax_condition = fields.Selection(
        selection=[
            ('none', 'State not defined'),
            ('01', 'Genera crédito IVA'),
            ('03', 'Bienes de Capital'),
            ('04', 'Gasto corriente no genera crédito'),
            ('05', 'Proporcionalidad')
        ],
        string='eInvoice tax condition',
        help='eInvoice tax condition',
        default="none")

    l10n_cr_edi_exempt = fields.Boolean(
        string='CR eInvoicing exempt',
        help="Set if this tax is fully or partially exempt for CR eInvoicing.")

    l10n_cr_edi_original_amount = fields.Float(
        string='CR eInvoicing original amount',
        digits=(16, 4),
        help="This is the original percertage for the tax before "
        "exemption. It is used for CR eInvoicing.")

    def _l10n_cr_edi_onchange_type_tax_use(self):
        if self.type_tax_use != 'purchase':
            self.l10n_cr_edi_tax_condition = 'none'

    @api.constrains('l10n_cr_edi_code', 'l10n_cr_edi_original_amount')
    def _check_tax_code_for_exempt(self):
        for record in self.filtered(lambda tax: tax.l10n_cr_edi_exempt and tax.l10n_cr_edi_code != '01'):
            raise ValidationError(_("The exemptions are allow just for IVA - Tax Code 1. Please check your tax "
                                    "configuration. You are using Tax code ").join(record.l10n_cr_edi_code))
