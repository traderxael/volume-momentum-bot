# Trading Journal Template — Volume Momentum Bot

Plantilla de diario de trading para usar con el bot Volume Momentum Bot.

## 📋 Estructura

### Página Principal: Dashboard
- Resumen semanal de P&L
- Win rate del mes
- Últimas 10 operaciones
- Indicadores clave

### Página: Registro de Operaciones
Cada operación tiene:
- Fecha y hora
- Par/Instrumento
- Dirección (Long/Short)
- Precio de entrada
- Stop Loss
- Take Profit
- Tamaño de posición
- R:R ratio
- Motivo de entrada (señal del indicador + contexto)
- Resultado (P&L)
- Screenshot del gráfico
- Notas y lecciones

## 📝 Plantilla Markdown (para Obsidian/Notion)

```markdown
# Trade Journal — {{DATE}}

## Operación #{{N}}
- **Fecha:** {{DATE}}
- **Par:** {{PAIR}}
- **Dirección:** {{LONG/SHORT}}
- **Entrada:** {{PRICE}}
- **Stop Loss:** {{SL}}
- **Take Profit:** {{TP}}
- **Tamaño:** {{SIZE}}
- **R:R:** {{RATIO}}

### Análisis Previo
- RSI Volumen: {{RSI_VOL}}
- Vol Ratio: {{VOL_RATIO}}
- Tendencia (EMA): {{TREND}}
- Momentum: {{MOMENTUM}}

### Motivo de Entrada
{{REASON}}

### Resultado
- **Salida:** {{EXIT_PRICE}}
- **P&L:** {{PNL}} USD
- **Resultado:** {{WIN/LOSS/BREAKEVEN}}

### Lecciones
{{LESSONS}}
```

## 📊 Métricas Semanales

| Métrica | Valor |
|---------|-------|
| Total trades | {{COUNT}} |
| Wins | {{WINS}} |
| Losses | {{LOSSES}} |
| Win rate | {{WIN_RATE}}% |
| P&L total | {{TOTAL_PNL}} USD |
| Avg R:R | {{AVG_RR}} |
| Mayor ganancia | {{MAX_WIN}} USD |
| Mayor pérdida | {{MAX_LOSS}} USD |

## 🔧 Setup Recomendado

1. Crea una página en Notion o Obsidian
2. Usa la plantilla de arriba para cada operación
3. Configura alertas del indicador Volume Momentum V1
4. Revisa el dashboard semanalmente
5. Ajusta parámetros según resultados

## 📧 Contacto
- **Autor:** Axael
- **Email:** mathialuke@gmail.com
- **Telegram:** @DREstebot