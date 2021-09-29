from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cr_first_limit = fields.Float(
        'First', related="company_id.l10n_cr_first_limit", digits='Payroll', readonly=False)
    l10n_cr_second_limit = fields.Float(
        'Second', related="company_id.l10n_cr_second_limit", digits='Payroll', readonly=False)
    l10n_cr_third_limit = fields.Float(
        'Third', related="company_id.l10n_cr_third_limit", digits='Payroll', readonly=False)
    l10n_cr_fourth_limit = fields.Float(
        'Fourth', related="company_id.l10n_cr_fourth_limit", digits='Payroll', readonly=False)
    l10n_cr_amount_per_child = fields.Float(
        'Amount per child', related="company_id.l10n_cr_amount_per_child", digits='Payroll',
        readonly=False)
    l10n_cr_amount_per_spouse = fields.Float(
        'Amount per spouse', related="company_id.l10n_cr_amount_per_spouse", digits='Payroll',
        readonly=False)
    l10n_cr_ccss = fields.Float("CCSS Workers' Fee %", related='company_id.l10n_cr_ccss', readonly=False)
    l10n_cr_bpdc = fields.Float("BPDC Workers' Fee %", related='company_id.l10n_cr_bpdc', readonly=False)
    l10n_cr_working_asociacion_solidarista = fields.Float(
        'Working ASOCIACIÓN SOLIDARISTA%', related='company_id.l10n_cr_working_asociacion_solidarista', readonly=False)
    l10n_cr_ins_email = fields.Char(
        'Email', related='company_id.l10n_cr_ins_email', readonly=False, help='Value to be used in the INS file.')
    l10n_cr_ins_number = fields.Char('Number', related='company_id.l10n_cr_ins_number', readonly=False)
    l10n_cr_ins_fax = fields.Char('Fax', related='company_id.l10n_cr_ins_fax', readonly=False)
    l10n_cr_ins_header = fields.Char(
        'Header', related='company_id.l10n_cr_ins_header', readonly=False, help='Header for TXT in INS file.')
