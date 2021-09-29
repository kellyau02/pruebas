from odoo import fields, models


class PaymentMethod(models.Model):
    """Payment Method for Costa Rica from DGT Data.
    Electronic documents need this information from such data.

    The payment method is an required attribute, to express the payment method
    of assets or services covered by the eInvoice.
    It is understood as a payment method legends such as
    credit card or debit card, check, deposit account, etc.
    Note: Odoo have the model payment.method, but this model need fields that
    we not need in this feature as partner_id, acquirer, etc., and they are
    there with other purpose, then a new model is necessary in order to avoid
    lose odoo's features"""

    _name = 'l10n_cr_edi.payment.method'
    _description = "Payment Method for Costa Rica from DGT Data"

    name = fields.Char(
        required=True,
        help='Payment way, is found in the DGT catalog.')
    code = fields.Char(
        required=True,
        help='Code defined by the DGT by this payment way. This value will '
        'be set in the XML node "MedioPago".')
    active = fields.Boolean(
        default=True,
        help='If this payment way is not used by the company could be '
        'deactivated.')
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        help='Optional fiscal position to compute payment methods account tax mapping. '
        'Should usually be used to Medical Services fiscal position. '
        'If not set, no general account mapping will be configured for l10n_cr_edi fiscal positions.',
        company_dependent=True,)
