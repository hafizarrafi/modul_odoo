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

        for (const line of lines) {
            itemMap[line.id] = {
                id: line.id,
                name: line.product_id[1],
                qty: line.quantity,
                prices: {},
                bestPrice: null,
            };
        }

        // build prices
        for (const v of vendorLines) {
            const lineId = v.rab_line_id[0];
            const vendorId = v.vendor_id[0];

            vendorMap[vendorId] ??= {
                id: vendorId,
                name: v.vendor_id[1],
            };

            itemMap[lineId].prices[vendorId] = {
                id: v.id,
                base: v.price,
                nego: v.negotiation_price,
                vendor_state: v.vendor_state,
                isBest: false,
            };
        }

        // compute best negotiated price per item
        for (const item of Object.values(itemMap)) {
            const candidates = Object.values(item.prices)
                .filter(p => p.vendor_state !== 'draft' && p.nego);

            if (candidates.length) {
                const best = Math.min(...candidates.map(p => p.nego));
                item.bestPrice = best;

                for (const p of candidates) {
                    if (p.nego === best) {
                        p.isBest = true;
                    }
                }
            }
        }

        this.state.vendors = Object.values(vendorMap);
        this.state.items = Object.values(itemMap);
    }


    async onChangeBasePrice(ev) {
        const id = Number(ev.target.dataset.id);
        const value = Number(ev.target.value);

        if (!id || isNaN(value)) return;

        try {
            await this.rabService.updateBasePrice(id, value);
            await this.reloadMatrix();
        } catch (err) {
            console.error("Gagal update harga awal", err);
            this.env.services.notification.add(
                "Gagal menyimpan harga awal",
                { type: "danger" }
            );
        }
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

        try {
            await this.rabService.resetFinal(id);
            await this.reloadMatrix();
        } catch (err) {
            console.error("Gagal reset final vendor", err);
            this.env.services.notification.add(
                "Gagal reset vendor final",
                { type: "danger" }
            );
        }
    }


    formatPrice(value) {
        return value ? value.toLocaleString("id-ID") : "-";
    }

    async onChangeNegotiationPrice(ev) {
        const vendorLineId = Number(ev.target.dataset.id);
        const value = Number(ev.target.value);

        if (!vendorLineId || isNaN(value)) {
            return;
        }

        try {
            await this.rabService.updateNegotiationPrice(
                vendorLineId,
                value
            );

            const { lines, vendorLines } =
                await this.rabService.fetchVendorMatrix(this.props.rabId);

            this.buildMatrix(lines, vendorLines);

        } catch (err) {
            console.error("Gagal update harga negosiasi", err);
            this.env.services.notification.add(
                "Gagal menyimpan harga negosiasi",
                { type: "danger" }
            );
        }
    }

}

VendorMatrix.template = "rab_management.VendorMatrix";
