/* Mapa de navegação da Área do Aluno: ids do design → rotas reais. */
export const LMS_ROUTES: Record<string, string> = {
  dashboard: "/painel",
  player: "/curso",
  courses: "/meus-cursos",
  catalog: "/catalogo",
  certificate: "/certificado",
  community: "/curso",
};

export function lmsHref(id: string): string {
  return LMS_ROUTES[id] ?? "/painel";
}

/** Deriva o id ativo a partir do pathname (para destacar item da sidebar). */
export function activeLmsId(pathname: string): string {
  if (pathname.startsWith("/meus-cursos")) return "courses";
  if (pathname.startsWith("/catalogo")) return "catalog";
  if (pathname.startsWith("/curso")) return "player";
  if (pathname.startsWith("/certificado")) return "certificate";
  return "dashboard";
}
