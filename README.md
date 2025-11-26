# LMSR Simulator

Um simulador interativo para mercados de previsão usando o mecanismo **Logarithmic Market Scoring Rule (LMSR)**. Esta aplicação permite simular trades em mercados binários (YES/NO) e analisar os resultados financeiros.

## 🚀 Funcionalidades

### Parâmetros Configuráveis
- **Base b Parameter**: Parâmetro de liquidez do mercado LMSR
- **Base Fee Rate**: Taxa de fee fixa aplicada em cada trade

### Gerenciamento de Trades
- ✅ Adicionar trades individualmente (Direction: YES/NO e quantidade de Shares)
- ✅ Importar trades em lote via JSON
- ✅ Visualizar todas as trades em tabela interativa
- ✅ Suporte para quantidade ilimitada de trades

### Simulação e Resultados
- Cálculo automático de custos usando fórmula LMSR
- Cálculo de fees dinâmicos
- Preço médio por share em cada trade
- Resumo financeiro completo:
  - Total Cost Paid
  - Total Fees Earned
  - Final Payout (baseado no resultado do mercado)
  - Net Worth (com cores condicionais: verde para lucro, vermelho para prejuízo)

### Interface
- Interface moderna e intuitiva
- Tabelas com scroll para grandes volumes de dados
- Feedback visual claro para seleções e resultados
- Botões coloridos para seleção de resultado final (YES verde, NO vermelho)

## 📦 Instalação

### Requisitos
- Python 3.7+
- Streamlit
- NumPy
- Pandas

### Instalação das Dependências

```bash
pip install -r requirements.txt
```

## 🎯 Como Usar

### Executar a Aplicação

```bash
streamlit run streamlit_app.py
```

### Adicionar Trades Manualmente

1. Configure os parâmetros (Base b e Base Fee Rate)
2. Selecione a direção (YES ou NO) e a quantidade de Shares
3. Clique em "Add Trade" para adicionar à lista

### Importar Trades via JSON

1. Clique em "Modelo JSON" para ver o formato esperado
2. Clique em "Importar JSON"
3. Cole o JSON no campo de texto
4. Clique em "Confirmar Importação"

#### Formato JSON

```json
{
  "trades": [
    {"direction": "YES", "shares": 10},
    {"direction": "NO", "shares": 5},
    {"direction": "YES", "shares": 20}
  ]
}
```

### Executar Simulação

1. Adicione as trades desejadas
2. Selecione o resultado final do mercado (YES ou NO)
3. Visualize os resultados na seção "Simulation Results"

## 📊 Entendendo os Resultados

### Métricas Exibidas

- **Cost Paid**: Custo de cada trade calculado pela fórmula LMSR
- **Avg. Price**: Preço médio por share (Cost Paid / Shares)
- **Fee Earned**: Taxa cobrada em cada trade
- **Total Cost Paid**: Soma de todos os custos pagos
- **Total Fees Earned**: Soma de todas as fees cobradas
- **Final Payout**: Quantidade de shares do resultado vencedor
- **Net Worth**: Lucro líquido (Fees + Costs - Payout)
  - Verde: Lucro positivo
  - Vermelho: Prejuízo

## 🔧 Tecnologias Utilizadas

- **Streamlit**: Framework para aplicações web interativas
- **NumPy**: Cálculos numéricos e matemáticos
- **Pandas**: Manipulação e exibição de dados em tabelas

## 📝 Sobre o LMSR

O **Logarithmic Market Scoring Rule (LMSR)** é um mecanismo de precificação usado em mercados de previsão. Ele garante liquidez constante e permite que traders comprem e vendam shares a qualquer momento, com preços determinados pela fórmula:

```
C(q_yes, q_no) = b * ln(e^(q_yes/b) + e^(q_no/b))
```

Onde:
- `b` é o parâmetro de liquidez
- `q_yes` e `q_no` são as quantidades de shares de cada resultado

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👤 Autor

**Iago Macedo**

---

Desenvolvido com ❤️ para simulação de mercados de previsão
