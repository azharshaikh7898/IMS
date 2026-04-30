import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/incident/:incidentId" element={<IncidentDetailPage />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
      </Routes>
    </Layout>
  );
}
