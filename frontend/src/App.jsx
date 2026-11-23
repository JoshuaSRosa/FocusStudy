
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  Navigate
} from "react-router-dom";

import { AuthProvider, useAuth } from "./context/AuthContext";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Cadastro from "./pages/Cadastro";
import "./App.css";

function Navbar() {
  const { usuario, logout } = useAuth();

  return (
    <nav className="navbar">
      <Link to="/" className="logo">
        FocusStudy
      </Link>

      <div className="nav-links">
        {!usuario && (
          <>
            <Link to="/login">Login</Link>
            <Link to="/cadastro">Cadastro</Link>
          </>
        )}

        {usuario && (
          <>
            <span className="usuario-nome">
              {usuario.nome}
            </span>

            <button type="button" onClick={logout}>
              Sair
            </button>
          </>
        )}
      </div>
    </nav>
  );
}

function Rotas() {
  const { usuario } = useAuth();

  return (
    <>
      <Navbar />

      <Routes>
        <Route path="/" element={<Home />} />

        <Route
          path="/login"
          element={
            usuario ? <Navigate to="/" replace /> : <Login />
          }
        />

        <Route
          path="/cadastro"
          element={
            usuario ? <Navigate to="/" replace /> : <Cadastro />
          }
        />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Rotas />
      </BrowserRouter>
    </AuthProvider>
  );
}