import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DocumentsPage } from "./pages/Documents";
import { TrendsPage } from "./pages/Trends";
import { UploadPage } from "./pages/Upload";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/trends" element={<TrendsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
