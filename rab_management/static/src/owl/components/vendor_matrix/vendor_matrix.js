/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class VendorMatrix extends Component {
    setup() {
        this.state = useState({
            vendors: [],
            items: [],
            loading: true,
        });

        this.rabService = useService("rabService");

        onWillStart(async () => {
            await this.reloadMatrix();
            this.state.loading = false;
        });
    }

    async reloadMatrix() {
        const { lines, vendorLines } =
            await this.rabService.fetchVendorMatrix(this.props.rabId);

        this.buildMatrix(lines, vendorLines);
    }

    buildMatrix(lines, vendorLines) {
        const vendorMap = {};
        const itemMap = {};

        // init item (1 baris RAB)
        for (const line of lines) {
            itemMap[line.id] = {
                id: line.id,
                name: line.product_id[1],
                qty: line.quantity,
                prices: {},

                // ringkasan keputusan
                selectedVendorId: null,
                selectedVendorName: null,
                selectedPrice: null,
            };
        }

        // map vendor comparison per item
        for (const v of vendorLines) {
            const lineId = v.rab_line_id[0];
            const vendorId = v.vendor_id[0];

            vendorMap[vendorId] ??= {
                id: vendorId,
                name: v.vendor_id[1],
            };

            itemMap[lineId].prices[vendorId] = {
                id: v.id,
                vendor_id: vendorId,
                base: v.price,
                nego: v.negotiation_price,
                vendor_state: v.vendor_state,
                isBest: false,
                isDimmed: false,
            };
        }

        // compute final summary + best candidate
        for (const item of Object.values(itemMap)) {
            const prices = Object.values(item.prices);

            // final decision (maksimal 1)
            const finalLine = prices.find(p => p.vendor_state === "final");
            if (finalLine) {
                item.selectedVendorId = finalLine.vendor_id;
                item.selectedVendorName =
                    vendorMap[finalLine.vendor_id]?.name || "-";
                item.selectedPrice = finalLine.nego;
            }

            // kandidat harga terbaik saat nego
            const candidates = prices.filter(
                p => p.vendor_state !== "draft" && p.nego > 0
            );

            if (!candidates.length) continue;

            const bestValue = Math.min(...candidates.map(p => p.nego));

            for (const p of candidates) {
                p.isBest = p.nego === bestValue;
                p.isDimmed = Boolean(finalLine) && p.vendor_state !== "final";
            }
        }

        this.state.vendors = Object.values(vendorMap);
        this.state.items = Object.values(itemMap);
    }

    async onChangeBasePrice(ev) {
        const id = Number(ev.target.dataset.id);
        const value = Number(ev.target.value);
        if (!id || isNaN(value)) return;

        await this.rabService.updateBasePrice(id, value);
        await this.reloadMatrix();
    }

    async onChangeNegotiationPrice(ev) {
        const id = Number(ev.target.dataset.id);
        const value = Number(ev.target.value);
        if (!id || isNaN(value)) return;

        await this.rabService.updateNegotiationPrice(id, value);
        await this.reloadMatrix();
    }

    async onSetNegotiation(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        await this.rabService.setNegotiation(id);
        await this.reloadMatrix();
    }

    async onSelectVendor(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        await this.rabService.setFinalVendor(id);
        await this.reloadMatrix();
    }

    async onResetFinal(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        if (!id) return;

        await this.rabService.resetFinal(id);
        await this.reloadMatrix();
    }

    formatPrice(value) {
        return value ? value.toLocaleString("id-ID") : "-";
    }
}

VendorMatrix.template = "rab_management.VendorMatrix";
