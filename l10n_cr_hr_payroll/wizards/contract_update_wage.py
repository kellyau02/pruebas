from odoo import fields, models


class UpdateContractWage(models.TransientModel):
    _name = 'update.contract.wage'
    _description = 'Allow update the wage in the contracts'

    l10n_cr_annual_increase = fields.Float('Annual Increase %')

    def action_apply(self):
        for contract in self.env['hr.contract'].browse(self._context.get('active_ids', [])):
            contract.wage = contract.wage + (contract.wage * (self.l10n_cr_annual_increase / 100))
            contract.l10n_cr_last_wage_update_annual = fields.datetime.now().date()
            contract.l10n_cr_last_percent_wage = self.l10n_cr_annual_increase
