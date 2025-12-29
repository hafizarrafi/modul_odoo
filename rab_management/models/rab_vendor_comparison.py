from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RabVendorComparison(models.Model):
    _name = 'rab.vendor.comparison'
    _description = 'RAB Vendor Comparison'

    rab_line_id = fields.Many2one(
        'rab.management.line',
        required=True,
        ondelete='cascade'
    )

    rab_id = fields.Many2one(
        'rab.management',
        related='rab_line_id.rab_id',
        store=True,
        readonly=True
    )

    product_id = fields.Many2one(
        related='rab_line_id.product_id',
        store=True,
        readonly=True
    )

    vendor_id = fields.Many2one(
        'res.partner',
        domain=[('supplier_rank', '>', 0)],
        required=True
    )

    price = fields.Float(required=True)
    is_selected = fields.Boolean(default=False)


    # KONDISI VALIDASI 1 VENDOR TERPILIH PER ITEM

    def write(self, vals):
        for rec in self:
            if rec.rab_line_id.rab_id.state == 'approved':
                raise UserError("Cannot modify vendor comparison on approved RAB.")
        return super().write(vals)

    @api.constrains('is_selected')
    def _check_single_vendor(self):
        for rec in self:
            if rec.is_selected:
                others = self.search([
                    ('rab_line_id', '=', rec.rab_line_id.id),
                    ('id', '!=', rec.id),
                    ('is_selected', '=', True),
                ])
                if others:
                    raise ValidationError(
                        "Only one vendor can be selected per RAB line."
                    )

    # AUTO SYNC FIELD KE RAB LINE

    def write(self, vals):
        res = super().write(vals)

        if vals.get('is_selected'):
            for rec in self:
                rec.rab_line_id.write({
                    'chosen_vendor_id': rec.vendor_id.id,
                    'purchase_price': rec.price,
                })

        return res
    
    
