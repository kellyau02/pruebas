from odoo import SUPERUSER_ID, api, tools


def migrate(cr, version):
    rename_extids_asebanca(cr)
    rename_records_asebanca(cr)
    rename_fields_asebanca(cr)


def rename_extids_asebanca(cr):
    """rename extenal IDs from "asebanca" to "asociacion_solidarista"

    Those external ID are renamed in data, so they need to be renamed in DB if already
    exist.
    """
    cr.execute("""
        UPDATE
            ir_model_data
        SET
            name = REPLACE(name, 'asebanca', 'asociacion_solidarista')
        WHERE
            module = 'l10n_cr_hr_payroll'
            AND name like '%asebanca%';
    """)


def rename_records_asebanca(cr):
    """Records need also to be renamed: salary rules, rule categories, etc"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Salary rules
    rules = env['hr.salary.rule'].search([('name', 'like', 'ASEBANCA')])
    for rule in rules:
        rule.write({'name': rule.name.replace('ASEBANCA', 'ASOCIACIÓN SOLIDARISTA')})

    # Salary rule category
    category = env.ref('l10n_cr_hr_payroll.hr_salary_rule_category_asociacion_solidarista')
    category.write({'name': 'ASOCIACIÓN SOLIDARISTA'})

    # Payslip type
    payslip_type = env.ref('l10n_cr_hr_payroll.hr_payslip_input_type_prestamo_asociacion_solidarista', False)
    if payslip_type:
        payslip_type.write({
            'code': 'prestamo_asociacion_solidarista',
            'name': 'Préstamo ASOCIACIÓN SOLIDARISTA',
        })


def rename_fields_asebanca(cr):
    if not tools.column_exists(cr, 'res_company', 'l10n_cr_working_asebanca'):
        return

    # Rename column
    tools.rename_column(
        cr, 'res_company',
        'l10n_cr_working_asebanca',
        'l10n_cr_working_asociacion_solidarista')

    # Rename fields
    cr.execute("""
        UPDATE
            ir_model_fields
        SET
            name = 'l10n_cr_working_asociacion_solidarista'
        WHERE
            name = 'l10n_cr_working_asebanca';
    """)
