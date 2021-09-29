
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.constrains('report_number_child')
    def _check_report_number_child(self):
        for employee in self:
            if employee.report_number_child < 0:
                raise UserError(_('Error! The number of child to report must be greater or equal to zero.'))
        return True

    @api.onchange('marital')
    def _onchange_marital(self):
        self.report_spouse = False

    report_spouse = fields.Boolean(help="If this employee reports his spouse for rent payment")
    report_number_child = fields.Integer(
        'Number of children to report', help="Number of children to report for rent payment")
    personal_email = fields.Char()

    def l10n_cr_get_days_ccss(self, days2pay, date_from, date_to):
        """Return the days to Incapacidades CCSS, if are the first 'days2pay' days return that number"""
        leave = self.env.ref('l10n_cr_hr_payroll.work_entry_type_sick_leave_inc_ccss')
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            '|', ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('holiday_status_id.active', '=', True),
            ('state', 'not in', ('cancel', 'refuse')),
            ('holiday_status_id.work_entry_type_id', '=', leave.id)
        ], limit=1)
        h_date_from = holidays.date_from.date()
        h_date_to = holidays.date_to.date()
        if (holidays.date_to - holidays.date_from).days > days2pay:
            h_date_to = holidays.date_from.date() + timedelta(days=days2pay)
        paid = (date_from - h_date_from).days
        if date_from > h_date_to or paid >= days2pay:
            return 0
        to_pay = (date_to - date_from if date_to < h_date_to else h_date_to - date_from).days + 1
        res = days2pay if to_pay >= days2pay else to_pay
        return res if res + paid <= days2pay else res - paid

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        """Render the options in the `marital` field to remove `cohabitant` option
        that is not a valid value on INS report.

        :return: Updated view architecture
        :rtype: xml
        """
        res = super(HrEmployee, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        if 'marital' not in res.get('fields', []):
            return res
        options = res['fields']['marital']['selection']
        if 'cohabitant' not in dict(options):
            return res
        options.remove(('cohabitant', dict(options)['cohabitant']))
        return res
