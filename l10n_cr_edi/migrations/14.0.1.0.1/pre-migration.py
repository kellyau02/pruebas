from odoo import SUPERUSER_ID, api


def convert_l10n_cr_edi_xml_treas_binary_as_attach(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    attachments = env['ir.attachment'].search([
        ('res_model', '=', 'account.move'),
        ('res_field', '=', 'l10n_cr_edi_xml_treas_binary'),
    ])

    for attachment in attachments:
        attachment.write({
            'res_field': False,
            'type': 'binary',
            'name': 'AHC- %s .xml' % attachment.res_name,
            'mimetype': 'application/xml',
            'description': 'Electronic message confirmation generated for the %s document.' % attachment.res_name,
        })


def migrate(cr, version):
    # Change the use of l10n_cr_edi_xml_treas_binary field to attachment to store DGT answer
    if not version:
        return
    convert_l10n_cr_edi_xml_treas_binary_as_attach(cr)
