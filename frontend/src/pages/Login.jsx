
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");

  const { login } = useAuth();
  const navigate = useNavigate();

  function entrar(event) {
    event.preventDefault();

    setErro("");
    setSucesso("");

    if (!email.includes("@")) {
      setErro("Digite um e-mail válido.");
      return;
    }

    if (senha.length < 6) {
      setErro("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    setSucesso("Formulário validado com sucesso!");
    login(email.trim().toLowerCase(), email.trim().toLowerCase());
    navigate("/");
    return;
  }

  return (
    <div className="container">
      <h1>Login</h1>

      <form onSubmit={entrar}>
        <label htmlFor="email">E-mail</label>
        <input
          type="email"
          placeholder="Seu e-mail"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label htmlFor="senha">Senha</label>
        <input
          type="password"
          placeholder="Sua senha"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
          minLength={6}
        />

        <button type="submit">Entrar</button>
      </form>

      {erro && (
        <p className="mensagem erro" role="alert">
          {erro}
        </p>
      )}

      {sucesso && (
        <p className="mensagem sucesso" role="status">
          {sucesso}
        </p>
      )}

      <p>Não tem uma conta?</p>
      <Link to="/cadastro">Cadastre-se</Link>
      <br />
      <Link to="/">Voltar ao início</Link>
    </div>
  );
}

export default Login;