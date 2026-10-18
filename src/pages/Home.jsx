import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Home() {
  const { usuario } = useAuth();
  
  return (
    <div className="container">
      <h1>FocusStudy</h1>
      <p>Plataforma para gestão de foco e rotina de estudos</p>

      {!usuario && (
        <>
        <Link to="/login" className="botao">
            Fazer login
        </Link>

        <Link to="/cadastro" className="botao">
            Criar conta
        </Link>
        </>
        )}

      {usuario && (
        <p>Você está conectado como {usuario.nome}, no curso {usuario.curso}.</p>
      )}
    </div>
  );
}

export default Home;