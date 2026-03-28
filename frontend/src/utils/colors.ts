// Persona colour palette — maps persona index to a CSS var
export const PERSONA_COLORS = [
  'var(--p0)', 'var(--p1)', 'var(--p2)',
  'var(--p3)', 'var(--p4)', 'var(--p5)',
];

const colorCache: Record<string, string> = {};
let colorIdx = 0;

export function getPersonaColor(name: string): string {
  if (!colorCache[name]) {
    colorCache[name] = PERSONA_COLORS[colorIdx % PERSONA_COLORS.length];
    colorIdx++;
  }
  return colorCache[name];
}

export function getInitial(name: string): string {
  const words = name.split(' ').filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}
