export const number = (value) => new Intl.NumberFormat('vi-VN').format(value);
export const percent = (value) => `${new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 }).format(value)}%`;
export function axisNumber(value) {
  if (Math.abs(value) >= 1000000) return `${number(value / 1000000)} triệu`;
  if (Math.abs(value) >= 1000) return `${number(value / 1000)} nghìn`;
  return number(value);
}
