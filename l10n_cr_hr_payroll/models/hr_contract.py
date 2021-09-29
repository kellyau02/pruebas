from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_cr_christmas_amount = fields.Monetary(
        'Christmas amount', tracking=True,
        help='If the employee saves an amount for christmas, set the amount to save each week.')
    l10n_cr_in_assebanca = fields.Boolean(
        'In ASOCIACIÓN SOLIDARISTA?',
        help='If is in ASOCIACIÓN SOLIDARISTA select this option to add the concepts for ASOCIACIÓN SOLIDARISTA in '
        'the payroll.')
    l10n_cr_last_wage_update = fields.Date(
        'Last Wage Update', help='Save the date when the Wage was updated. Is used to get the wage in the '
        'payslip, to consider if it was changed in the period.', tracking=True)
    l10n_cr_last_wage_update_annual = fields.Date(
        'Last Wage Annual Update', help='Save the date when the Wage was updated. Is used to get the retroactive by '
        'wage adjust if this is not in the first week of the year.', tracking=True)
    l10n_cr_last_percent_wage = fields.Float(
        'Annual Increase %', help='Save the last annual increase in percent', tracking=True)
    l10n_cr_previous_wage = fields.Monetary(
        'Previous Wage', tracking=True, help='Save the last wage.')
    l10n_cr_school_salary = fields.Float(
        'School salary', tracking=True,
        help='If the company offers amount for school salary, set the percentage for the employee.')

    def get_retroactive_wage(self, payslip):
        """Return the retroactive for wage if the increase wasn't in the first January week"""
        if not self.l10n_cr_last_wage_update_annual or not self.l10n_cr_last_percent_wage:
            return 0
        if payslip.date_from <= self.l10n_cr_last_wage_update_annual <= payslip.date_to:
            days = (payslip.date_from - self.l10n_cr_last_wage_update_annual.replace(month=1, day=1)).days
            increase = self.wage / (1 + self.l10n_cr_last_percent_wage)
            return increase / 365 * days
        return 0

    @api.constrains('state')
    def constraint_check_state(self):
        if len(self.employee_id.contract_ids.filtered(lambda con: con.state == 'open')) > 1:
            raise ValidationError(_('Only is possible an open contract per employee.'))

    def get_seniority(self, date_from=False, date_to=False, method='r'):
        """Return seniority between contract's date_start and date_to or today

        :param date_from: start date (default contract.date_start)
        :type date_from: str
        :param date_to: end date (default today)
        :type date_to: str
        :param method: {'r', 'a'} kind of values returned
        :type method: str
        :return: a dict with the values years, months, days.
            These values can be relative or absolute.
        :rtype: dict
        """
        self.ensure_one()
        datetime_start = date_from or self.date_start
        date = date_to or fields.Date.today()
        relative_seniority = relativedelta(date, datetime_start)
        if method == 'r':
            return {'years': relative_seniority.years,
                    'months': relative_seniority.months,
                    'days': relative_seniority.days}
        return {'years': relative_seniority.years,
                'months': (relative_seniority.months + relative_seniority
                           .years * 12),
                'days': (date - datetime_start).days + 1}

    @api.onchange('wage')
    def _onchange_l10n_cr_wage(self):
        for contract in self:
            contract.l10n_cr_last_wage_update = fields.datetime.now().date()
            contract.l10n_cr_previous_wage = self._origin.wage
