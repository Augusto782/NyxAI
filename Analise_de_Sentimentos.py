import os

os.environ['HUGGINGFACE_HUB_CACHE'] = r'C:\meu_cache_huggingface'

from transformers import pipeline



# -----------------------------------------------------------

# 1. INICIALIZAÇÃO GLOBAL DO MODELO BERT (FAÇA ISSO APENAS UMA VEZ!)

# -----------------------------------------------------------

try:

    GLOBAL_BERT_CLASSIFIER = pipeline(

        "sentiment-analysis",

        model="nlptown/bert-base-multilingual-uncased-sentiment",

        device=-1 # -1 para CPU

        )

    print("DEBUG: Modelo BERT para análise de sentimento carregado com sucesso.")

except Exception as e:

    GLOBAL_BERT_CLASSIFIER = None

    print(f"ERRO CRÍTICO: Não foi possível carregar o modelo BERT. A ferramenta de análise de emoções estará indisponível. Detalhes: {e}")

# -----------------------------------------------------------



# ... Definição da sua função de ferramenta aqui ...

def analisar_emocoes_local_bert(text):

    """

    Função de ferramenta que usa o classificador global.

    """

    if GLOBAL_BERT_CLASSIFIER is None:

        return "ERRO: O classificador BERT não está disponível para uso."

    try:

        response = GLOBAL_BERT_CLASSIFIER(text) # Usa o objeto carregado uma única vez

        resultado = response[0]

        label_raw = resultado['label']

        score = resultado['score']

        # Mapeamento para termos amigáveis (ajuste conforme o seu gosto)

        MAPPING = {

            '5 stars': "FORTE FELICIDADE / AMOR",

            '4 stars': "FELICIDADE / SATISFAÇÃO",

            '3 stars': "NEUTRO / EQUILIBRADO",

            '2 stars': "INSATISFAÇÃO / LEVE TRISTEZA",

            '1 star': "FORTE RAIVA / TRISTEZA"

            }

        emocao = MAPPING.get(label_raw, label_raw)

        return f"Análise de Emoções (BERT):\n- Emoção Principal: {emocao}\n- Confiança: {score*100:.2f}%"

    except Exception as e:

        return f"Erro na inferência do BERT: {e}"