import { products, suppliers, purchaseOrders } from "../mock/data.js";
const demo = (data) => Promise.resolve({ data, source: "demo" });
export const inventoryService = { list: () => demo(products) };
export const supplierService = { list: () => demo(suppliers) };
export const purchaseOrderService = { list: () => demo(purchaseOrders) };
export const forecastService = { get: () => demo([]) };
export const procurementService = { list: () => demo([]) };
export const assistantService = {
  ask: (question) =>
    demo({
      question,
      answer: "This demo assistant uses illustrative responses only.",
    }),
};
