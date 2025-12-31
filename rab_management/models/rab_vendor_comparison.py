  
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

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

    # SATU-SATUNYA WRITE
    def write(self, vals):
        for rec in self:
            # lock kalau RAB approved
            if rec.rab_line_id.rab_id.state == 'approved':
                raise UserError(
                    "Cannot modify vendor comparison on approved RAB."
                )

        res = super().write(vals)

        # sync ke RAB line hanya kalau selected
        if vals.get('is_selected'):
            for rec in self:
                if rec.is_selected:
                    rec.rab_line_id.write({
                        'chosen_vendor_id': rec.vendor_id.id,
                        'purchase_price': rec.price,
                    })

        return res
    

    def action_select_vendor(self):
        self.ensure_one()
        # unselect vendor lain
        others = self.search([
            ('rab_line_id', '=', self.rab_line_id.id),
            ('id', '!=', self.id),
        ])
        others.write({'is_selected': False})

        # select vendor ini
        self.write({'is_selected': True})



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
