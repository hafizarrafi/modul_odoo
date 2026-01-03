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
        string='Vendor',
        required=True,
        domain=[('contact_type', 'in', ['vendor', 'both'])],
    )

    price = fields.Float(string="Quoted Price", required=True)
    is_selected = fields.Boolean(default=False)

        # === PRICE HINT (REFERENCE ONLY) ===
    last_purchase_price = fields.Float(
        string="Last Purchase Price (Reference)",
        compute="_compute_last_purchase",
        store=True,
        readonly=True,
        help="Reference only. Does not affect current price."
    )

    last_purchase_date = fields.Datetime(
        string="Last Purchase Date",
        compute="_compute_last_purchase",
        store=True,
        readonly=True
    )


    # =========================
    # WRITE (SAFE VERSION)
    # =========================
    def write(self, vals):
        for rec in self:
            if rec.rab_id.state == 'approved' and any(
                k in vals for k in ['vendor_id', 'price', 'is_selected']
            ):
                raise UserError(
                    "Cannot modify vendor or price on approved RAB."
                )

        res = super().write(vals)

        # sync ke RAB line hanya kalau vendor dipilih
        if vals.get('is_selected'):
            for rec in self.filtered('is_selected'):
                rec.rab_line_id.write({
                    'chosen_vendor_id': rec.vendor_id.id,
                    'purchase_price': rec.price,
                })

        return res

    # =========================
    # ACTION: SELECT VENDOR
    # =========================
    def action_select_vendor(self):
        self.ensure_one()

        # unselect vendor lain
        self.search([
            ('rab_line_id', '=', self.rab_line_id.id),
            ('id', '!=', self.id),
        ]).write({'is_selected': False})

        self.write({'is_selected': True})

    # =========================
    # CONSTRAINT
    # =========================
    @api.constrains('is_selected')
    def _check_single_vendor(self):
        for rec in self:
            if rec.is_selected:
                count = self.search_count([
                    ('rab_line_id', '=', rec.rab_line_id.id),
                    ('is_selected', '=', True),
                ])
                if count > 1:
                    raise ValidationError(
                        "Only one vendor can be selected per RAB line."
                    )
    @api.depends('vendor_id', 'product_id')
    def _compute_last_purchase(self):
        for rec in self:
            rec.last_purchase_price = 0.0
            rec.last_purchase_date = False

            if not rec.vendor_id or not rec.product_id:
                continue

            line = self.env['purchase.order.line'].search([
                ('product_id', '=', rec.product_id.id),
                ('partner_id', '=', rec.vendor_id.id),
                ('order_id.state', 'in', ['purchase', 'done']),
            ], order='id desc', limit=1)

            if line:
                rec.last_purchase_price = line.price_unit
                rec.last_purchase_date = line.order_id.date_order
