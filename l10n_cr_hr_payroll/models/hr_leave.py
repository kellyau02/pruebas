from odoo import api, fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    l10n_cr_edi_payslip_use_calendar_days = fields.Boolean(
        'Use Calendar Days?',
        help="If True, the holiday's related will to consider the calendar days"
    )


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.depends('date_from', 'date_to', 'employee_id', 'holiday_status_id')
    def _compute_number_of_days(self):
        result = super()._compute_number_of_days()
        calendar_leaves = self.filtered(lambda h: h.holiday_status_id.l10n_cr_edi_payslip_use_calendar_days
                                        and h.date_from and h.date_to)
        for holiday in calendar_leaves:
            holiday.number_of_days = (holiday.date_to - holiday.date_from).days + 1
        return result
