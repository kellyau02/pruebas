# Copyright 2016 Vauxoo
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cr_edi_test_env = fields.Boolean(
        related='company_id.l10n_cr_edi_test_env', string="CR PAC test environment",
        readonly=False,
        help='Enable when the certificate environment is test')

    l10n_cr_edi_client_api_key = fields.Char(
        related='company_id.l10n_cr_edi_client_api_key', readonly=False)

    l10n_cr_edi_addenda_gs1 = fields.Boolean(
        'Addenda Retail Committee Standard of GS1',
        help='If is select will be installed the addenda for Retail Committee Standard of GS1.')
