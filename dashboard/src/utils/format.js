export function esNumeroValido(val) {
  if (typeof val === 'number') return !isNaN(val);
  if (typeof val === 'string') {
    return !isNaN(parseFloat(val.replace(/[^0-9.-]/g, '')));
  }
  return false;
}

export function parseNumero(val) {
  if (typeof val === 'number') return val;
  if (typeof val === 'string') {
    const parsed = parseFloat(val.replace(/[^0-9.-]/g, ''));
    return isNaN(parsed) ? null : parsed;
  }
  return null;
}

export function formatearPrecio(num) {
  if (num === null || num === undefined || num === Infinity) return '-';
  const parsed = parseNumero(num);
  if (parsed === null) return String(num);
  return new Intl.NumberFormat('es-AR').format(parsed);
}

export function normalizarTexto(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}
