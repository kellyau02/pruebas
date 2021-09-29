from datetime import timedelta, datetime, time

from odoo import models, fields, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    schedule_pay = fields.Selection([
        ('fortnightly', 'Fortnightly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
        ], 'Scheduled Pay', index=True, readonly=True, states={'draft': [('readonly', False)]})

    def action_payslips_done(self):
        self.ensure_one()
        # using search instead of filtered to keep performance in batch with many payslips
        payslips = self.slip_ids.search(
            [('id', 'in', self.slip_ids.ids), ('state', '=', 'draft')])
        for payslip in payslips:
            try:
                with self.env.cr.savepoint():
                    payslip.action_payslip_done()
            except UserError as e:
                payslip.message_post(
                    body=_('Error during the process: %s') % e)

    def action_payslips_compute_sheet(self):
        self.ensure_one()
        # using search instead of filtered to keep performance in batch with many payslips
        self.slip_ids.search(
            [('id', 'in', self.slip_ids.ids), ('state', '=', 'draft')]).compute_sheet()

    def action_payroll_sent(self):
        """Send email for all signed payslips"""
        self.ensure_one()
        template = self.env.ref(
            'l10n_cr_hr_payroll.email_template_payslip', False)
        mail_composition = self.env['mail.compose.message']
        for payslip in self.slip_ids.filtered(
                lambda p: (p.state == 'done' and not p.sent and p.employee_id.work_email)):
            res = mail_composition.create({
                'model': 'hr.payslip',
                'res_id': payslip.id,
                'template_id': template and template.id or False,
                'composition_mode': 'comment'})
            res.onchange_template_id_wrapper()
            mail_composition |= res
        # send all
        mail_composition.action_send_mail()


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    sent = fields.Boolean(readonly=True, default=False, copy=False,
                          help="It indicates that the payslip has been sent.")
    l10n_cr_allow_adjust = fields.Boolean(
        'Allow Adjust', copy=False, tracking=True,
        help='If the payslip has input for adjust must be selected this option, to confirm that is correct that '
        'input.')

    # Get total payment per month
    def get_qty_previous_payment(self, employee):
        payslip_ids = []
        if self.date_to.month < 10:
            first = str(self.date_to.year) + "-" + "0" + str(self.date_to.month) + "-" + "01"
        else:
            first = str(self.date_to.year) + "-" + str(self.date_to.month) + "-" + "01"
        first_date = datetime.strptime(first, '%Y-%m-%d')
        payslip_ids = self.search([
            ('employee_id', '=', employee.id),
            ('date_to', '>=', first_date),
            ('date_to', '<', self.date_from)])
        return len(payslip_ids)

    # Get the previous payslip for an employee. Return all payslip that are in
    # the same month than current payslip
    def get_previous_payslips(self, employee):
        payslip_list = []
        month_date_to = self.date_to.month
        year_date_to = self.date_to.year
        payslips = self.search([
            ('employee_id', '=', employee.id), ('date_to', '<=', self.date_to), ('id', '!=', self.id)])

        for empl_payslip in payslips:
            if (empl_payslip.date_to.month == month_date_to) and (empl_payslip.date_to.year == year_date_to):
                payslip_list.append(empl_payslip)
        return payslip_list

    # get SBA for employee (Gross salary for an employee)
    def get_sba(self, employee):
        sba = 0.0
        payslip_list = self.get_previous_payslips(employee)  # list of previous payslips
        for payslip in payslip_list:
            for line in payslip.line_ids.filtered(lambda pl: pl.code == 'BRUTO'):
                if payslip.credit_note:
                    sba -= line.total
                else:
                    sba += line.total
        return sba

    # get previous rent
    def get_previous_rent(self, employee):
        rent = 0.0
        payslip_list = self.get_previous_payslips(employee)  # list of previous payslips
        for payslip in payslip_list:
            for line in payslip.line_ids.filtered(lambda pl: pl.code == 'RENTA'):
                if payslip.credit_note:
                    rent -= line.total
                else:
                    rent += line.total
        return rent

    # Get quantity of days between two dates
    def days_between_days(self, date_from, date_to):
        return abs((date_to - date_from).days)

    # Get number of payments per month
    def qty_future_payments(self):
        payments = 0

        dbtw = (self.days_between_days(self.date_from, self.date_to)) + 1

        next_date = self.date_to + timedelta(days=dbtw)
        month_date_to = self.date_to.month

        if month_date_to == 2:
            next_date = next_date - timedelta(days=2)

        month_date_next = next_date.month

        while month_date_to == month_date_next:
            next_date = next_date + timedelta(days=dbtw)
            month_date_next = next_date.month
            payments += 1
        return payments

    def action_payslip_send(self):
        """This function opens a window to compose an email, with the payslip template message loaded by default"""
        assert len(self.ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('l10n_cr_hr_payroll', 'email_template_payslip')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'hr.payslip',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def compute_total_rent(self, inputs, employee, categories):
        """ This function computes, based on previous gross salary and future
            base salary, the rent amount for current payslip. This is a
            "dynamic" way to compute amount rent for each payslip
        """

        # If the payslip is a refund, we need to use the same amount calculated above
        if self.credit_note:
            original_name = self.name.replace(_('Refund: '), '')
            original_payslip = self.search([
                ('name', '=', original_name), ('employee_id', '=', employee.id),
                ('date_to', '=', self.date_to), ('date_from', '=', self.date_from)], limit=1)
            for line in original_payslip.line_ids:
                if line.code == 'RENTA':
                    return line.total
            return 0.0

        # Get total payments
        future_payments = self.qty_future_payments()
        actual_payment = 1

        # Update payments amount
        sba = self.get_sba(employee)
        sbp = categories.TOTALS
        sbf = categories.BASIC * future_payments
        sbt = sba + sbp + sbf

        # Compute rent
        rent_empl_total = self.compute_rent_employee(self.company_id, employee, sbt)  # Rent for a complete month
        total_paid_rent = self.get_previous_rent(employee)  # Rent already paid
        total_curr_rent = (rent_empl_total + total_paid_rent) / (future_payments + actual_payment)

        return total_curr_rent

    def compute_rent_employee(self, company, employee, sbt):
        """This function is designed to be called from python code in the salary rule.
        It receive as parameters the variables that can be used by default in
        python code on salary rule.

        This function compute rent for a employee"""
        total = 0.0

        limit1 = company.l10n_cr_first_limit  # From hr.conf.settings, it's in company
        limit2 = company.l10n_cr_second_limit
        limit3 = company.l10n_cr_third_limit
        limit4 = company.l10n_cr_fourth_limit

        percent1 = 0.10
        percent2 = 0.15
        percent3 = 0.20
        percent4 = 0.25

        wife_amount = company.l10n_cr_amount_per_spouse
        child_amount = company.l10n_cr_amount_per_child
        children_numbers = employee.report_number_child

        total += max(0.0, sbt - limit4) * percent4
        total += max(0.0, min(sbt, limit4) - limit3) * percent3
        total += max(0.0, min(sbt, limit3) - limit2) * percent2
        total += max(0.0, min(sbt, limit2) - limit1) * percent1

        if total:
            if employee.report_spouse:
                total = max(0.0, total - wife_amount)
            total = max(0.0, total - (child_amount * children_numbers))
        return total

    def get_overtimes_in_period(self):
        """Get the overtimes in period for the employee"""
        attendances = self.employee_id.attendance_ids.filtered(
            lambda att: att.check_in.date() >= self.date_from and att.check_out.date() <= self.date_to)
        hours = 0
        for att in attendances:
            diff = att.check_out - att.check_in
            days, seconds = diff.days, diff.seconds
            hours += days * 24 + seconds // 3600
        day_from = datetime.combine(self.date_from, time.min)
        day_to = datetime.combine(self.date_to, time.max)
        return hours - self.employee_id.get_work_days_data(day_from, day_to, compute_leaves=False).get('hours')

    def action_payslip_done(self):
        for order in self.filtered(lambda ord: not ord.l10n_cr_allow_adjust):
            if order.input_line_ids.filtered(lambda input: input.code == 'ajuste' and input.amount):
                raise UserError(_('The payroll for %s has the "Adjust" input and the check to allow that input is '
                                  'not activated.') % order.employee_id.name)
        return super(HrPayslip, self).action_payslip_done()

    def action_payslip_cancel(self):
        """Overwrite method when state is done, to allow cancel payslip in done
        """
        to_cancel = self.filtered(lambda r: r.state == 'done')
        to_cancel.write({'state': 'cancel'})
        self.refresh()
        return super(HrPayslip, self).action_payslip_cancel()

    def _get_worked_day_lines(self):
        """Overwrite WORK100 to get all days in the period"""
        result = super()._get_worked_day_lines()
        result = self._set_leaves_calendar_days_count(result)
        hours_per_day = result[0]['number_of_hours'] / result[0]['number_of_days'] if (
            result and result[0]['number_of_days'] != 0) else 0
        total = sum([line['number_of_days'] for line in result])
        work_entry = self.env.ref('hr_work_entry.work_entry_type_attendance')
        out_contract = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
        date_from = max(self.date_from, self.contract_id.date_start)
        days = self.contract_id.get_seniority(date_from, self.date_to, 'a')['days']
        days_out_start, days_out_end = self._get_out_of_contract_days()
        total -= sum([line['number_of_days'] for line in result if line['work_entry_type_id'] == out_contract.id])
        # Adjust Attendances
        for line in result:
            if line['work_entry_type_id'] == work_entry.id:
                line['number_of_days'] = line['number_of_days'] + days - total - days_out_end

        # Include Out of contract line
        out_of_contract_days = days_out_start + days_out_end
        if out_of_contract_days:
            out_contract_line = [line for line in result if line['work_entry_type_id'] == out_contract.id]
            vals = {
                'sequence': out_contract.sequence,
                'work_entry_type_id': out_contract.id,
                'number_of_days': out_of_contract_days,
                'number_of_hours': hours_per_day * out_of_contract_days,
            }
            if out_contract_line:
                out_contract_line[0].update(vals)
            else:
                result.append(vals)

        # Check there are all days in the period, refill with attendences if not
        payslip_period_days = (self.date_to - self.date_from).days + 1
        worked_days = sum([line['number_of_days'] for line in result])
        if worked_days < payslip_period_days and result:
            days = payslip_period_days - worked_days
            result.append({
                'sequence': work_entry.sequence,
                'work_entry_type_id': work_entry.id,
                'number_of_days': days,
                'number_of_hours': hours_per_day * days,
            })
        return result

    def _get_out_of_contract_days(self):
        """If the contract doesn't cover the whole payslip period, get how many days are out of contract period"""
        contract = self.contract_id
        if not contract:
            return 0, 0
        days_out_start = (contract.date_start - self.date_from).days if contract.date_start > self.date_from else 0
        days_out_end = 0 if not contract.date_end or contract.date_end >= self.date_to else (
            self.date_to - contract.date_end).days
        return days_out_start, days_out_end

    def _set_leaves_calendar_days_count(self, worked_day_lines):
        """This method sets on the worked_day_lines the missing days that are out of normal employee's work schedule
        in the period of hr.leaves that uses calendar days

        - Get which days the employee does not work being 0 Monday and 6 Sunday
        - Get week days that normally the employee does not work
        - Get the specific dates when the employee does not work in the payslip period
        - for each date, search if there is at least one hr.leave that:
            Uses calendar days
            The date is beetween leave period
            Is for the payslip employee
        If there is at least one, count a day, save the count grouping by hr.leave hr.work.entry.type
        - For each group, check in worked_day_lines. If there is a dict with work_entry_type_id set,
        add the days count to its number_of_days and number_of_hours. If not, create a new dict in the
        worked_day_lines list to create a new worked day on the payslip.
        """
        work_days = self.contract_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
        not_work_days = list(set(['0', '1', '2', '3', '4', '5', '6']) - set(work_days))

        leave_days = {}
        for day in range((self.date_to - self.date_from).days + 1):
            date = self.date_from + timedelta(days=day)
            if str(date.weekday()) not in not_work_days:
                continue
            leave = self.env['hr.leave'].search([
                ('holiday_status_id.l10n_cr_edi_payslip_use_calendar_days', '=', True),
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
                ('date_from', '<', fields.datetime.combine(date, time(0))),
                ('date_to', '>', fields.datetime.combine(date, time(0))),
            ], limit=1)
            if not leave:
                continue
            # Use entry type as key and count as value
            # If the entry type is already set, sum 1, if not set the count as 1
            entry_type_id = leave.holiday_status_id.work_entry_type_id.id
            leave_days[entry_type_id] = leave_days[entry_type_id] + 1 if leave_days.get(entry_type_id) else 1

        # Add the work entry type and count to the result/worked_day_lines dict
        for work_entry_type, days_count in leave_days.items():
            is_entry_set = False
            for line in worked_day_lines:
                if line['work_entry_type_id'] == work_entry_type:
                    line['number_of_days'] = line['number_of_days'] + days_count
                    line['number_of_hours'] = line['number_of_hours'] + days_count * 8
                    is_entry_set = True
                    break

            if is_entry_set:
                continue
            worked_day_lines.append({
                'sequence': 25,
                'work_entry_type_id': work_entry_type,
                'number_of_days': days_count,
                'number_of_hours': 8.0 * days_count
            })
        return worked_day_lines
