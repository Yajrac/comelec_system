export function calculateAge(value) {
  if (!value) return '';
  const [year, month, day] = value.split('-').map(Number);
  const born = new Date(year, month - 1, day);
  const today = new Date();
  if (born.getFullYear() !== year || born.getMonth() !== month - 1 || born.getDate() !== day || born >= today) return '';
  return String(today.getFullYear() - year - (today.getMonth() < month - 1 || (today.getMonth() === month - 1 && today.getDate() < day) ? 1 : 0));
}
