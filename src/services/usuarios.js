const CHAVE = "usuarios";

export function buscarUsuarios() {
  return JSON.parse(
    localStorage.getItem(CHAVE) || "[]"
  );
}

export function cadastrarUsuario({ nome, email }) {
  const usuarios = buscarUsuarios();

  const existe = usuarios.some(
    (usuario) => usuario.email === email
  );

  if (existe) {
    throw new Error("Este e-mail já está cadastrado.");
  }

  const novoUsuario = {
    id: crypto.randomUUID(),
    nome,
    email,
    criadoEm: new Date().toISOString(),
  };

  usuarios.push(novoUsuario);

  localStorage.setItem(
    CHAVE,
    JSON.stringify(usuarios)
  );

  return novoUsuario;
}