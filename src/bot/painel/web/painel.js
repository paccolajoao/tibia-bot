// Cliente WebSocket do painel. Recebe eventos de telemetria e atualiza a UI.
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const MAX_LINHAS = 250;
  let ws = null;

  function conectar() {
    const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
    ws = new WebSocket(url);

    ws.onopen = () => marcarConexao(true);
    ws.onclose = () => {
      marcarConexao(false);
      setTimeout(conectar, 1500); // reconecta
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      tratar(msg);
    };
  }

  function tratar(msg) {
    switch (msg.tipo) {
      case "estado": aplicarEstado(msg); break;
      case "decisao": aplicarDecisao(msg); break;
      case "raciocinio": adicionarLinha(msg); break;
      case "stats": aplicarStats(msg); break;
      case "quadro": $("quadro").src = "data:image/jpeg;base64," + msg.jpeg_base64; break;
      case "deteccao": aplicarDeteccao(msg); break;
    }
  }

  function aplicarEstado(s) {
    if (s.hp_pct != null) {
      $("hp-preench").style.width = clamp(s.hp_pct) + "%";
      $("hp-valor").textContent = s.hp_pct.toFixed(0) + "%";
    }
    if (s.mana_pct != null) {
      $("mana-preench").style.width = clamp(s.mana_pct) + "%";
      $("mana-valor").textContent = s.mana_pct.toFixed(0) + "%";
    }
    if (s.hp_confianca != null) $("hp-conf").textContent = s.hp_confianca.toFixed(2);

    const badge = $("badge-estado");
    badge.textContent = s.estado_execucao;
    badge.className = "badge " + classeEstado(s.estado_execucao);

    const foco = $("badge-foco");
    foco.textContent = "foco: " + (s.janela_focada ? "sim" : "não");
    foco.className = "badge " + (s.janela_focada ? "badge-on" : "badge-pausado");

    $("badge-backend").textContent = "captura: " + s.backend_captura;
    $("badge-fps").textContent = (s.fps || 0).toFixed(0) + " fps";
    $("st-fps").textContent = (s.fps || 0).toFixed(0);
    $("st-tick").textContent = s.tick;
  }

  function aplicarDecisao(d) {
    $("dec-acao").textContent = rotuloAcao(d);
    $("dec-motivo").textContent = d.motivo;
    $("dec-comp").textContent = d.comportamento;
    $("dec-tecla").textContent = d.tecla ? d.tecla.toUpperCase() : (d.acao === "CLICAR" ? "clique" : "—");
  }

  function rotuloAcao(d) {
    if (d.acao === "PRESSIONAR_TECLA") return "PRESSIONAR " + (d.tecla || "").toUpperCase();
    if (d.acao === "CLICAR") return "CLICAR" + ((d.dados && d.dados.recurso) ? " (" + d.dados.recurso + ")" : "");
    return "monitorando";
  }

  function aplicarStats(s) {
    $("st-curas").textContent = s.curas;
    $("st-mana").textContent = s.pocoes_mana;
    if (s.ataques != null) $("st-ataques").textContent = s.ataques;
    if (s.refeicoes != null) $("st-refeicoes").textContent = s.refeicoes;
    if (s.saques != null) $("st-saques").textContent = s.saques;
    $("st-uptime").textContent = formatarTempo(s.uptime_s);
  }

  function aplicarDeteccao(d) {
    const c = d.criaturas;
    if (!c) {
      $("det-criaturas").textContent = "—";
      $("det-alvo").textContent = "—";
      $("det-conf").textContent = "—";
      return;
    }
    $("det-criaturas").textContent = c.n;
    $("det-alvo").textContent = c.alvo_atual ? "sim" : "não";
    $("det-conf").textContent = (c.confianca != null ? c.confianca.toFixed(2) : "—");
  }

  function adicionarLinha(r) {
    const log = $("log");
    const perto = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
    const div = document.createElement("div");
    div.className = "linha " + (r.nivel || "info");
    const hora = new Date().toLocaleTimeString();
    div.innerHTML = '<span class="ts">' + hora + "</span>" + escapar(r.texto);
    log.appendChild(div);
    while (log.childElementCount > MAX_LINHAS) log.removeChild(log.firstChild);
    if (perto) log.scrollTop = log.scrollHeight;
  }

  function enviar(cmd) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ cmd }));
  }

  function marcarConexao(ok) {
    const b = $("badge-conexao");
    b.textContent = ok ? "conectado" : "desconectado";
    b.className = "badge " + (ok ? "badge-on" : "badge-off");
  }

  function classeEstado(e) {
    if (e === "RODANDO") return "badge-on";
    if (e === "PAUSADO") return "badge-pausado";
    if (e === "PARADO" || e === "PANICO") return "badge-off";
    return "";
  }

  function clamp(v) { return Math.max(0, Math.min(100, v)); }
  function escapar(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  function formatarTempo(s) {
    s = Math.floor(s || 0);
    if (s < 60) return s + "s";
    const m = Math.floor(s / 60);
    if (m < 60) return m + "m " + (s % 60) + "s";
    return Math.floor(m / 60) + "h " + (m % 60) + "m";
  }

  $("btn-pausar").onclick = () => enviar("pausar");
  $("btn-retomar").onclick = () => enviar("retomar");
  $("btn-parar").onclick = () => enviar("parar");

  conectar();
})();
