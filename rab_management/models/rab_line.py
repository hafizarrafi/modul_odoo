from odoo import models, fields, api
from odoo.exceptions import UserError


class RabManagementLine(models.Model):
    _name = 'rab.management.line'
    _description = 'RAB Line'

    # --- Relasi utama ---
    rab_id = fields.Many2one(
        'rab.management',
        ondelete='cascade',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Produk',
        required=True
    )

    # Nama baris otomatis mengikuti produk yang dipilih
    name = fields.Char(
        string='Deskripsi',
        compute='_compute_name',
        store=True
    )

    quantity = fields.Float(
        default=1.0,
        digits='Product Unit of Measure'
    )

    # --- Perbandingan vendor ---
    vendor_line_ids = fields.One2many(
        'rab.vendor.comparison',
        'rab_line_id',
        string='Perbandingan Vendor'
    )

    # Vendor yang dipilih sebagai hasil akhir
    chosen_vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor Terpilih',
        readonly=True
    )

    # Harga beli akhir yang diambil dari vendor terpilih
    purchase_price = fields.Monetary(
        string='Harga Beli',
        readonly=True
    )

    # --- Margin & harga jual ---
    margin_type = fields.Selection(
        [
            ('absolute', 'Nominal'),
            ('percentage', 'Persentase'),
        ],
        string='Tipe Margin',
        default='absolute',
        required=True
    )

    margin_value = fields.Float(
        string='Nilai Margin'
    )

    # Harga jual dihitung dari harga beli + margin
    sale_price = fields.Monetary(
        string='Harga Jual',
        compute='_compute_sale_price',
        store=True,
        readonly=True
    )

    # --- Total ---
    subtotal = fields.Monetary(
        compute='_compute_subtotal',
        store=True
    )

    currency_id = fields.Many2one(
        related='rab_id.currency_id',
        store=True,
        readonly=True
    )

    # Penanda bahwa baris terkunci ketika RAB sudah disetujui
    is_locked = fields.Boolean(
        compute='_compute_is_locked',
        store=True
    )

    # Tahapan global proses perbandingan vendor
    vendor_comparison_stage = fields.Selection(
        [
            ('draft', 'Draft'),
            ('negotiation', 'Negosiasi'),
            ('selected', 'Terpilih'),
        ],
        default='draft',
        tracking=True,
        string='Tahap Perbandingan Vendor'
    )

    # ------------------------------------------------------------------
    # Proteksi perubahan data
    # ------------------------------------------------------------------

    def write(self, vals):
        # Baris RAB tidak boleh diubah jika RAB sudah disetujui
        for rec in self:
            if rec.rab_id.state == 'approved':
                raise UserError(
                    "Baris RAB yang sudah disetujui tidak dapat diubah."
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Method compute
    # ------------------------------------------------------------------

    @api.depends('rab_id.state')
    def _compute_is_locked(self):
        for rec in self:
            rec.is_locked = rec.rab_id.state == 'approved'

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name if line.product_id else ''

    @api.depends('purchase_price', 'margin_type', 'margin_value')
    def _compute_sale_price(self):
        for line in self:
            if not line.purchase_price:
                line.sale_price = 0.0
                continue

            if line.margin_type == 'absolute':
                line.sale_price = line.purchase_price + (line.margin_value or 0.0)

            elif line.margin_type == 'percentage':
                line.sale_price = line.purchase_price * (
                    1 + (line.margin_value or 0.0) / 100
                )

    @api.depends('quantity', 'sale_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.sale_price

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def action_open_rab_line(self):
        self.ensure_one()

        # Perbarui data perbandingan vendor berdasarkan histori pembelian
        # Dipicu secara eksplisit saat user membuka RAB Line
        self.env['rab.vendor.comparison'].auto_populate_from_last_purchase(self)

        return {
            'type': 'ir.actions.act_window',
            'name': 'RAB Line',
            'res_model': 'rab.management.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
