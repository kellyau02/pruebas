# Copyright 2016 Vauxoo

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cr_edi_vat_type = fields.Selection(
        related='partner_id.l10n_cr_edi_vat_type',
        store=True,
        readonly=False)
    l10n_cr_edi_canton_id = fields.Many2one(
        related='partner_id.l10n_cr_edi_canton_id',
        store=True,
        readonly=False)
    l10n_cr_edi_district_id = fields.Many2one(
        related='partner_id.l10n_cr_edi_district_id',
        store=True,
        readonly=False)
    l10n_cr_edi_neighborhood_id = fields.Many2one(
        related='partner_id.l10n_cr_edi_neighborhood_id',
        store=True,
        readonly=False)
    l10n_cr_edi_economic_activity_ids = fields.Many2many(
        'l10n.cr.account.invoice.economic.activity',
        readonly=False)
    l10n_cr_edi_tradename = fields.Char(
        string='Tradename',
        help='Tradename')

    #   It is the key to the consumption of services of the distributor
    l10n_cr_edi_client_api_key = fields.Char(string="Api Key", size=256)

    #   It is the environment in which the certificate is being used
    #   Could be staging or production
    l10n_cr_edi_test_env = fields.Boolean(
        string="Environment", default=False,
        help='Enable when the certificate environment is test')


class AccountInvoiceEconomicActivity(models.Model):
    """New  model to manage the economic activities in Costa Rica, they are
    specified by Treasury
    """

    _name = 'l10n.cr.account.invoice.economic.activity'
    _description = 'Company Economic Activity'
    _order = 'code'

    code = fields.Char(help='The activity code', required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(code)',
         'The code of the economic activity must be unique!')
    ]
