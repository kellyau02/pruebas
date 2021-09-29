from odoo import _, models
from odoo.tests.common import Form


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False):
        moves = super()._create_invoices(grouped=grouped, final=final)
        for move in moves:
            move_form = Form(move)
            for line in range(0, len(move.invoice_line_ids)):
                with move_form.invoice_line_ids.edit(line) as line_form:
                    line_form.l10n_cr_edi_amount_discount = line_form.l10n_cr_edi_amount_discount
            move_form.save()
        return moves


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """Coupons for the order are considered.
        The price unit in te coupon line is updated to 0, and the discount is
        applied in the other lines."""
        res = super()._prepare_invoice_line(**optional_values)
        order = self.order_id
        program = order.applied_coupon_ids.program_id or order.no_code_promo_program_ids or order.code_promo_program_id
        avoid_delivery = order.company_id.l10n_cr_edi_not_delivery_discount
        if self.is_reward_line and program.discount_apply_on == 'on_order':
            res.update({
                'name': _('%s\nTotal Discount:%s\nCoupon:%s') % (
                    res.get('name'),
                    res.get('price_unit', 0),
                    order.applied_coupon_ids.display_name),
                'price_unit': 0,
            })
        if not self.is_reward_line and program.discount_apply_on == 'on_order':
            if 'is_delivery' in self._fields and self.is_delivery and avoid_delivery:
                return res
            delivery_product = order.order_line.filtered('is_delivery') if 'is_delivery' in self._fields else False
            delivery_amount = delivery_product.price_total if delivery_product and avoid_delivery else 0
            reward = order.order_line.filtered('is_reward_line')
            total = sum((order.order_line - reward).mapped('price_total')) - delivery_amount
            factor = abs(sum(reward.mapped('price_total'))) / total if total else 1
            res.update({
                'l10n_cr_edi_amount_discount': factor * self.price_unit,
            })
        return res
