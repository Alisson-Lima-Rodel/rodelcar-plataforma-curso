/* Área do Aluno — dados reais via TanStack Query (auth-api.ts):
   dashboard, matrículas, player do curso, progresso e certificado.
   Aqui ficou só o tipo de KPI usado pelo cartão do painel. */

export interface Kpi {
  label: string;
  value: string;
  sub: string;
  delta: string;
  trend: "up" | "flat";
  icon: string;
  spark: number[];
}
