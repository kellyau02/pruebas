# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

LIST_PROVIDER = [('tilopay',_('Tilopay'))]

class PaymentTilopays(models.Model):
    _inherit = 'payment.acquirer'
    
    provider = fields.Selection(selection_add=LIST_PROVIDER,
                    ondelete={'tilopay': 'set default'})

    # name = fields.Char(String='Name')
    # description = fields.Html('Description')
    # provider = fields.Selection(
    #     selection=[('Pago manual', 'Formulario de pago personalizado')], string='Provider',
    #     default='Pago manual', required=True)
    # state = fields.Selection([
    #     ('disabled', 'Disabled'),
    #     ('enabled', 'Enabled'),
    #     ('test', 'Test Mode')], required=True, default='disabled', copy=False)
    # company_id = fields.Many2one(
    #     'res.company', 'Company',
    #     default=lambda self: self.env.company.id, required=True)
    # website_id = fields.Many2one(
    #     'website', 'Website', required=True)
    tilopay_email_account = fields.Char(String='Correo electrónico')
    tilopay_password_account = fields.Char(String='Password')
    tilopay_key_account = fields.Char(String='Key')