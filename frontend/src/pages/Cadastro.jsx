
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { cadastrarUsuario } from "../services/usuarios"; // Backend, troque isso

function Cadastro() {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [curso, setCurso] = useState("");
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  function cadastrar(event) {
    event.preventDefault();

    setErro("");
    setSucesso("");

    if (nome.trim().length < 2) {
      setErro("Digite seu nome.");
      return;
    }

    if (!email.includes("@")) {
      setErro("Digite um e-mail válido.");
      return;
    }

    if (senha.length < 6) {
      setErro("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    if (senha !== confirmarSenha) {
      setErro("As senhas não coincidem.");
      return;
    }

    if (curso.length < 1) {
      setErro("Digite o nome do seu curso.");
      return;
    }

    try {
        cadastrarUsuario({
            nome: nome.trim(),
            email: email.trim().toLowerCase(),
            curso: curso.trim(),
        });

        login(nome.trim(), email.trim().toLowerCase(), curso.trim());
        navigate("/");
        } catch (error) {
        setErro(error.message);
    }
  }

  return (
    <div className="container">
      <h1>Cadastro</h1>

      <form onSubmit={cadastrar}>
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
          minLength={6}
          required
        />

        <label htmlFor="confirmarSenha">Confirmar Senha</label>
        <input
          type="password"
          placeholder="Confirme sua senha"
          value={confirmarSenha}
          onChange={(e) => setConfirmarSenha(e.target.value)}
          minLength={6}
          required
        />

        <label htmlFor="nome">Nome</label>
        <input
          type="text"
          placeholder="Seu nome completo"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          required
        />

        <label htmlFor="curso">Curso</label>
        <input
          type="text"
          placeholder="Nome do seu curso"
          value={curso}
          onChange={(e) => setCurso(e.target.value)}
          required
        />

        <button type="submit">Cadastrar</button>
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

      <p>Já tem uma conta?</p>
      <Link to="/login">Fazer login</Link>
      <br />
      <Link to="/">Voltar ao início</Link>
    </div>
  );
}

export default Cadastro;