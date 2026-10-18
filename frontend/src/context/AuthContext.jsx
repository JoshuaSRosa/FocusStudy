
import { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem("sessao") || "null"
      );
    } catch {
      return null;
    }
  });

  function login(nome, email, curso = "Indefinido") {
    const sessao = { nome, email, curso };

    localStorage.setItem("sessao", JSON.stringify(sessao));
    setUsuario(sessao);
  }

  function logout() {
    localStorage.removeItem("sessao");
    setUsuario(null);
  }

  return (
    <AuthContext.Provider value={{ usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
