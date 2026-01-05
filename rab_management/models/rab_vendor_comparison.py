from odoo import models, fields, api
from odoo.exceptions import UserError


class RabVendorComparison(models.Model):
    _name = 'rab.vendor.comparison'
    _description = 'Perbandingan Vendor per RAB Line'

    # ------------------------------------------------------------------
    # Relasi utama
    # ------------------------------------------------------------------

    # Relasi ke baris RAB
    rab_line_id = fields.Many2one(
        'rab.management.line',
        required=True,
        ondelete='cascade'
    )

    # Shortcut ke RAB induk
    rab_id = fields.Many2one(
        'rab.management',
        related='rab_line_id.rab_id',
        store=True,
        readonly=True
    )

    # Produk yang dibandingkan (mengikuti RAB Line)
    product_id = fields.Many2one(
        related='rab_line_id.product_id',
        store=True,
        readonly=True
    )

    # Vendor yang ikut dalam perbandingan
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('contact_type', 'in', ['vendor', 'both'])],
    )

    # Harga awal (hasil auto dari histori atau input manual)
    price = fields.Float(
        string="Harga Awal",
        required=True
    )

    # Harga hasil negosiasi
    negotiation_price = fields.Float(
        string="Harga Negosiasi",
        help="Harga akhir hasil negosiasi yang digunakan saat memilih vendor."
    )

    # Penanda bahwa harga tidak boleh di-update otomatis
    price_locked = fields.Boolean(
        string="Harga Dikunci",
        default=False
    )

    # ------------------------------------------------------------------
    # State perbandingan vendor
    # ------------------------------------------------------------------

    vendor_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('negotiation', 'Negosiasi'),
            ('final', 'Final'),
            ('cancelled', 'Tidak Terpilih'),
        ],
        default='draft',
        tracking=True,
        store=True,
    )

    # ------------------------------------------------------------------
    # Flag bantu untuk UI
    # ------------------------------------------------------------------

    # Menandakan apakah sudah ada vendor final di RAB Line ini
    has_final_vendor = fields.Boolean(
        compute="_compute_has_final_vendor",
        store=False
    )

    # ------------------------------------------------------------------
    # Histori pembelian (referensi saja)
    # ------------------------------------------------------------------

    last_purchase_price = fields.Float(
        compute="_compute_last_purchase",
        store=True,
        readonly=True
    )

    last_purchase_date = fields.Datetime(
        compute="_compute_last_purchase",
        store=True,
        readonly=True
    )

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

    @api.onchange('vendor_state')
    def _onchange_vendor_state(self):
        for rec in self:
            # Saat masuk tahap negosiasi:
            # - set harga negosiasi awal dari harga awal
            # - kunci harga agar tidak di-update otomatis
            if rec.vendor_state == 'negotiation':
                if not rec.negotiation_price:
                    rec.negotiation_price = rec.price
                rec.price_locked = True

    # ------------------------------------------------------------------
    # Auto populate dari histori pembelian
    # ------------------------------------------------------------------

    @api.model
    def auto_populate_from_last_purchase(self, rab_line):
        product = rab_line.product_id
        if not product:
            return

        po_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', product.id),
            ('order_id.state', 'in', ['purchase', 'done']),
            ('partner_id.contact_type', 'in', ['vendor', 'both']),
        ], order='id desc')

        vendors_seen = set()

        for line in po_lines:
            vendor = line.partner_id
            if vendor.id in vendors_seen:
                continue
            vendors_seen.add(vendor.id)

            existing = self.search([
                ('rab_line_id', '=', rab_line.id),
                ('vendor_id', '=', vendor.id),
            ], limit=1)

            if existing:
                # Update harga hanya jika masih draft
                # dan belum pernah disentuh user
                if existing.vendor_state == 'draft' and not existing.price_locked:
                    existing.with_context(auto_update=True).write({
                        'price': line.price_unit
                    })
            else:
                # Tambahkan vendor baru dari histori pembelian
                self.create({
                    'rab_line_id': rab_line.id,
                    'vendor_id': vendor.id,
                    'price': line.price_unit,
                })

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_set_negotiation(self):
        for rec in self:
            # Tidak boleh negosiasi jika sudah ada vendor final
            if rec.has_final_vendor:
                raise UserError(
                    "Vendor final sudah dipilih. Silakan reset terlebih dahulu."
                )

            if rec.vendor_state != 'draft':
                continue

            rec.write({
                'vendor_state': 'negotiation',
                'price_locked': True,
            })

    def action_set_final(self):
        self.ensure_one()
        rab_line = self.rab_line_id

        # Hanya vendor dalam tahap negosiasi yang bisa dipilih
        if self.vendor_state != 'negotiation':
            return

        # Harga negosiasi wajib diisi
        if not self.negotiation_price:
            raise UserError(
                "Harap isi harga negosiasi sebelum memilih vendor final."
            )

        # Pastikan belum ada vendor final lain
        existing_final = self.search([
            ('rab_line_id', '=', rab_line.id),
            ('vendor_state', '=', 'final'),
        ], limit=1)

        if existing_final:
            raise UserError("Vendor final sudah dipilih.")

        # Minimal 2 vendor pernah masuk negosiasi
        negotiation_count = self.search_count([
            ('rab_line_id', '=', rab_line.id),
            ('vendor_state', '=', 'negotiation'),
        ])

        if negotiation_count < 2:
            raise UserError(
                "Minimal harus ada 2 vendor dalam tahap negosiasi."
            )

        # SEMUA vendor lain set ke cancelled
        other_vendors = self.search([
            ('rab_line_id', '=', rab_line.id),
            ('id', '!=', self.id),
        ])
        other_vendors.write({'vendor_state': 'cancelled'})

        # Set vendor ini sebagai final
        self.write({'vendor_state': 'final'})

        # Sinkronkan hasil ke RAB Line
        rab_line.write({
            'chosen_vendor_id': self.vendor_id.id,
            'purchase_price': self.negotiation_price,
            'vendor_comparison_stage': 'selected',
        })


    def action_reset_final(self):
        self.ensure_one()
        if self.vendor_state != 'final':
            return

        rab_line = self.rab_line_id

        # Kembalikan semua vendor ke draft
        affected = self.search([
            ('rab_line_id', '=', rab_line.id),
            ('vendor_state', 'in', ['final', 'cancelled']),
        ])

        affected.write({
            'vendor_state': 'draft',
            'price_locked': False,
        })

        # Reset hasil di RAB Line
        rab_line.write({
            'chosen_vendor_id': False,
            'purchase_price': 0.0,
            'vendor_comparison_stage': 'draft',
        })

    # ------------------------------------------------------------------
    # Override write
    # ------------------------------------------------------------------

    def write(self, vals):
        for rec in self:
            # Jika user mengubah harga secara manual,
            # kunci agar tidak di-update otomatis
            if 'price' in vals and not self.env.context.get('auto_update'):
                vals['price_locked'] = True

            # Harga tidak boleh diubah setelah final
            if rec.vendor_state == 'final' and (
                'price' in vals or 'negotiation_price' in vals
            ):
                raise UserError(
                    "Harga vendor final tidak dapat diubah."
                )

            # Harga negosiasi hanya boleh diubah saat negosiasi
            if 'negotiation_price' in vals and rec.vendor_state != 'negotiation':
                raise UserError(
                    "Harga negosiasi hanya dapat diubah saat tahap negosiasi."
                )

        return super().write(vals)

    # ------------------------------------------------------------------
    # Compute helpers
    # ------------------------------------------------------------------

    @api.depends('rab_line_id')
    def _compute_has_final_vendor(self):
        for rec in self:
            rec.has_final_vendor = bool(self.search([
                ('rab_line_id', '=', rec.rab_line_id.id),
                ('vendor_state', '=', 'final'),
            ], limit=1))

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
