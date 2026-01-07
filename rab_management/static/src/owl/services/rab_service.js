/** @odoo-module */

import { registry } from "@web/core/registry";

export const rabService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        return {
            async setFinalVendor(vendorComparisonId) {
                return orm.call(
                    "rab.vendor.comparison",
                    "action_set_final",
                    [[vendorComparisonId]]
                );
            },

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

            async setNegotiation(vendorComparisonId) {
                return orm.call(
                    "rab.vendor.comparison",
                    "action_set_negotiation",
                    [[vendorComparisonId]]
                );
            }

        };
    },
};

registry.category("services").add("rabService", rabService);
