const FULL_ACCESS_ROLES = ['Gerente', 'Administrador'];
const DESKTOP_ACCESS_ROLES = [...FULL_ACCESS_ROLES, 'Recepcao', 'Comercial'];

const normalizeRole = (role) =>
  (role || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();

export const getUsuarioLocal = () => {
  try {
    const usuarioJSON = localStorage.getItem('usuario');
    return usuarioJSON ? JSON.parse(usuarioJSON) : null;
  } catch (error) {
    return null;
  }
};

export const clearAuthStorage = () => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('usuario');
};

export const isDesktopUser = (usuario) => {
  const tipo = normalizeRole(usuario?.tipo);
  return DESKTOP_ACCESS_ROLES.some((role) => normalizeRole(role) === tipo);
};

export const hasFullAccess = (usuario) => {
  const tipo = normalizeRole(usuario?.tipo);
  return FULL_ACCESS_ROLES.some((role) => normalizeRole(role) === tipo);
};

export const canAccessDesktopRoute = (path, usuario) => {
  if (!isDesktopUser(usuario)) {
    return false;
  }

  if (hasFullAccess(usuario)) {
    return true;
  }

  return ['/agenda', '/clientes'].includes(path);
};
