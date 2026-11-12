import { Routes, Route } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout.jsx";
import Dashboard from "../pages/Dashboard.jsx";
import Inventory from "../pages/Inventory.jsx";
import Forecasting from "../pages/Forecasting.jsx";
import Suppliers from "../pages/Suppliers.jsx";
import Procurement from "../pages/Procurement.jsx";
import Assistant from "../pages/Assistant.jsx";
import PurchaseOrders from "../pages/PurchaseOrders.jsx";
import NotFound from "../pages/NotFound.jsx";
export default function Router() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/forecasting" element={<Forecasting />} />
        <Route path="/suppliers" element={<Suppliers />} />
        <Route path="/procurement" element={<Procurement />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/orders" element={<PurchaseOrders />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
