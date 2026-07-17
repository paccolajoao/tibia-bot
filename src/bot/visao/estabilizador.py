"""Estabiliza leituras de barra (HP/Mana) entre frames.

`barra_recursos.ler_percentual_barra` é uma função pura por-frame e tem um ponto
cego: uma barra TOTALMENTE uniforme (toda vazia OU toda cheia — ex.: ocluída por um
overlay escuro/claro) sai com confiança 1.0 (`_confianca` linha 92-93). Ou seja, uma
oclusão pode virar "HP 0% confiável" (-> panic-heal à toa) ou "HP 100% confiável"
(-> suprime TODA cura enquanto o char apanha). Como isso exige memória entre frames,
mora aqui (fora da função pura).

`EstabilizadorBarra` mantém estado por barra e:
- rejeita um EXTREMO UNIFORME (~0% ou ~100%) que não seja corroborado pelo frame
  anterior E coerente com o último valor bom (salto impossível tipo 30%->100% em 66ms);
- em leitura rejeitada OU de baixa confiança (starvation em burst), SEGURA o último
  valor bom recente (hold pessimista, TTL curto) para a cura não ficar cega no meio do
  combate; sem histórico fresco, devolve confiança 0.0 (as camadas ignoram).

Testável offline (só estado + aritmética; nada de OpenCV/captura).
"""

from __future__ import annotations

from bot.visao.tipos import LeituraBarra

# defaults (ajustáveis pelo construtor)
EPS_EXTREMO = 1.0  # |valor-0| ou |valor-100| <= isto conta como extremo uniforme
TTL_HOLD_S = 0.4  # por quanto tempo o último valor bom segura a decisão
SALTO_MAX_PCT = 60.0  # variação máx. plausível vs. último bom p/ aceitar um extremo


class EstabilizadorBarra:
    def __init__(
        self,
        confianca_minima: float,
        *,
        ttl_s: float = TTL_HOLD_S,
        salto_max_pct: float = SALTO_MAX_PCT,
        eps: float = EPS_EXTREMO,
    ):
        self.confianca_minima = confianca_minima
        self.ttl_s = ttl_s
        self.salto_max_pct = salto_max_pct
        self.eps = eps
        self._bom_valor: float | None = None
        self._bom_ts: float | None = None
        self._valor_anterior: float | None = None

    def estabilizar(self, leitura: LeituraBarra | None, ts: float) -> LeituraBarra | None:
        if leitura is None:
            return None

        valor = leitura.percentual
        conf = leitura.confianca
        aceito = conf >= self.confianca_minima

        # extremo uniforme (0%/100%): principal fonte de leitura-fantasma por oclusão.
        if aceito and (valor <= self.eps or valor >= 100.0 - self.eps):
            corroborado = self._valor_anterior is not None and abs(self._valor_anterior - valor) <= self.eps
            coerente = (
                self._bom_valor is None
                or self._bom_ts is None
                or (ts - self._bom_ts) > self.ttl_s
                or abs(valor - self._bom_valor) <= self.salto_max_pct
            )
            if not (corroborado and coerente):
                aceito = False

        self._valor_anterior = valor

        if aceito:
            self._bom_valor = valor
            self._bom_ts = ts
            return leitura

        # rejeitada/baixa confiança: segura o último bom recente (hold pessimista) p/
        # a cura continuar agindo sobre o último HP conhecido em vez de ficar cega.
        if self._bom_valor is not None and self._bom_ts is not None and (ts - self._bom_ts) <= self.ttl_s:
            return LeituraBarra(self._bom_valor, max(conf, self.confianca_minima))

        # sem histórico fresco: força confiança baixa -> as camadas ignoram a leitura.
        return LeituraBarra(valor, 0.0)
