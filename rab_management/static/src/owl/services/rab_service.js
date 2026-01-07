/** @odoo-module */

import { registry } from "@web/core/registry";

export const rabService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        return {
            async fetchVendorMatrix(rabId) {
                const lines = await orm.searchRead(
                    "rab.management.line",
                    [["rab_id", "=", rabId]],
                    ["id", "product_id", "quantity"]
                );

                const lineIds = lines.map(l => l.id);

                const vendorLines = await orm.searchRead(
                    "rab.vendor.comparison",
                    [["rab_line_id", "in", lineIds]],
                    [
                        "id",
                        "rab_line_id",
                        "vendor_id",
                        "price",
                        "negotiation_price",
                        "vendor_state",
                    ]
                );

                return { lines, vendorLines };
            },

            // draft → negotiation
            async setNegotiation(id) {
                return orm.call(
                    "rab.vendor.comparison",
                    "action_set_negotiation",
                    [[id]]
                );
            },

            // negotiation → final
            async setFinalVendor(id) {
                return orm.call(
                    "rab.vendor.comparison",
                    "action_set_final",
                    [[id]]
                );
            },

            // final → draft (RESET)
            async resetFinal(id) {
                return orm.call(
                    "rab.vendor.comparison",
                    "action_reset_final",
                    [[id]]
                );
            },

            async updateBasePrice(id, price) {
                return orm.write(
                    "rab.vendor.comparison",
                    [id],
                    { price }
                );
            },


            // inline nego price
            async updateNegotiationPrice(id, price) {
                return orm.write(
                    "rab.vendor.comparison",
                    [id],
                    { negotiation_price: price }
                );
            },
        };
    },
};

registry.category("services").add("rabService", rabService);
