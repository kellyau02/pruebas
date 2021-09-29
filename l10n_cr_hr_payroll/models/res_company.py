from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cr_first_limit = fields.Float(digits='Payroll')
    l10n_cr_second_limit = fields.Float(digits='Payroll')
    l10n_cr_third_limit = fields.Float(digits='Payroll')
    l10n_cr_fourth_limit = fields.Float(digits='Payroll')
    l10n_cr_amount_per_child = fields.Float(digits='Payroll')
    l10n_cr_amount_per_spouse = fields.Float(digits='Payroll')
    l10n_cr_ccss = fields.Float("CCSS Workers' Fee %")
    l10n_cr_bpdc = fields.Float("BPDC Workers' Fee %")
    l10n_cr_working_asociacion_solidarista = fields.Float('Working ASOCIACIÓN SOLIDARISTA%')
    l10n_cr_ins_email = fields.Char(help='Value to be used in the INS file.')
    l10n_cr_ins_header = fields.Char('Header', help='Header for TXT in INS file.')
    l10n_cr_ins_number = fields.Char('Number')
    l10n_cr_ins_fax = fields.Char('Fax')
