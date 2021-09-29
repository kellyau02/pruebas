import time
from datetime import timedelta
from odoo.tests.common import TransactionCase


class HRPayroll(TransactionCase):

    def setUp(self):
        super(HRPayroll, self).setUp()
        self.payslip_obj = self.env['hr.payslip']
        self.employee = self.env.ref('hr.employee_qdp')
        self.contract = self.env.ref('hr_payroll.hr_contract_gilles_gravie')
        self.struct = self.env.ref('l10n_cr_hr_payroll.payroll_structure_data_l10n_cr')

    def test_001_payslip(self):
        """Verify rules code is correct"""
        payroll = self.create_payroll()
        payroll.action_payslip_done()
        self.assertEqual(payroll.state, 'done', 'Payroll cannot be validated.')

    def test_002_out_of_contract(self):
        """Test out of contract worked days and recompute worked days method"""
        self.remove_leaves()
        payroll = self.create_payroll()
        # Check the contract starts much time before
        self.contract.date_start = payroll.date_from - timedelta(days=405)
        self.contract.date_end = payroll.date_to - timedelta(days=5)
        self._check_out_of_contract_config(payroll, 5)
        # Check the contract starts after payslip period and has no end
        self.contract.date_start = payroll.date_from + timedelta(days=5)
        self.contract.date_end = False
        self._check_out_of_contract_config(payroll, 5)
        # Check the contract starts after payslip period and has end after payslip period
        self.contract.date_start = payroll.date_from + timedelta(days=5)
        self.contract.date_end = payroll.date_to + timedelta(days=35)
        self._check_out_of_contract_config(payroll, 5)
        # Check if the contract ends before the period
        self.contract.date_start = payroll.date_from
        self.contract.date_end = payroll.date_to - timedelta(days=5)
        self._check_out_of_contract_config(payroll, 5)
        # Check if the contract starts after payslip period and ends before the period
        self.contract.date_start = payroll.date_from + timedelta(days=3)
        self.contract.date_end = payroll.date_to - timedelta(days=3)
        self._check_out_of_contract_config(payroll, 6)

    def test_003_inabilities_ccss(self):
        """Ensure that inabilities are created"""
        self.remove_leaves()
        leave = self.env['hr.leave'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('l10n_cr_hr_payroll.inc_ccss').id,
            'request_date_from': '%s-%s-01' % (time.strftime('%Y'), time.strftime('%m')),
            'request_date_to': '%s-%s-03' % (time.strftime('%Y'), time.strftime('%m')),
            'number_of_days': 3,
        })
        leave._compute_date_from_to()
        leave.action_approve()
        payroll = self.create_payroll()
        payroll.action_refresh_from_work_entries()
        payroll.action_payslip_done()
        self.assertEqual(payroll.state, 'done', 'Payroll cannot be validated.')

    def _check_out_of_contract_config(self, payroll, expected_out_of_contract_days, expected_lines=2):
        total_period_days = (payroll.date_to - payroll.date_from).days + 1
        payroll.action_refresh_from_work_entries()
        worked_lines = payroll.worked_days_line_ids
        self.assertEqual(len(worked_lines), expected_lines, '%d Lines expected' % expected_lines)
        self.assertEqual(sum(worked_lines.mapped('number_of_days')), total_period_days,
                         'The total sum of number of days must be the total of days in the period, %d days' %
                         total_period_days)
        self.assertTrue(len(worked_lines.mapped('name')) == len(set(worked_lines.mapped('name'))),
                        'No concept should be repeated in worked days lines')
        self.assertFalse([item for item in worked_lines.mapped('number_of_days') if item < 1],
                         'There should be no lines with negative or zero days in the worked days')
        out_contract_line = worked_lines.filtered(lambda w: w.name == 'Out of Contract')
        self.assertTrue(out_contract_line, 'There must be an Out of Contract line')
        self.assertEqual(out_contract_line.number_of_days, expected_out_of_contract_days,
                         'There must be %s days out of contract' % expected_out_of_contract_days)

    def remove_leaves(self):
        leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)])
        leaves.action_refuse()
        leaves.action_draft()
        leaves.unlink()

    def create_payroll(self):
        return self.payslip_obj.create({
            'name': 'Payslip Test',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.struct.id,
            'date_from': '%s-%s-01' % (
                time.strftime('%Y'), time.strftime('%m')),
            'date_to': '%s-%s-15' % (time.strftime('%Y'), time.strftime('%m')),
        })
