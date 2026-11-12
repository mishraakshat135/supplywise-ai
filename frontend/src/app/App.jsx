import { useState } from "react";
import Router from "./router.jsx";
import { Toast } from "../components/common/UI.jsx";
export default function App() {
  const [toast, setToast] = useState("");
  window.showToast = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 3200);
  };
  return (
    <>
      <Router />
      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </>
  );
}
