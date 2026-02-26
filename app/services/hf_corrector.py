from huggingface_hub import InferenceClient
from loguru import logger

from typing import Tuple

async def correct_text_with_hf(text: str, token: str) -> Tuple[str, bool]:
    """
    Sends the extracted text to a Hugging Face model to correct syntax and spelling errors.
    Returns a tuple (corrected_text, is_truncated).
    """
    try:
        # Using a reliable instruction-following lightweight model
        client = InferenceClient(token=token)
        
        # Truncating raw text to fit in prompt token limit (approx 3000 chars for safety)
        # Production ready apps would chunk this into parts.
        is_truncated = len(text) > 3500
        safe_text = text[:3500] if is_truncated else text
        
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Tu es un assistant expert spécialisé dans le nettoyage de textes extraits par OCR (reconnaissance optique de caractères).
Ta mission est de corriger les fautes d'orthographe et les erreurs de grammaire causées par l'OCR.
DE PLUS, tu dois IMPÉRATIVEMENT nettoyer le texte en supprimant :
- Les numéros de page
- Les en-têtes (headers) et pieds de page (footers)
- Les artefacts de mise en page, les caractères parasites et les "décorateurs"

Conserve l'intégralité du texte principal sans en modifier le sens.
Renvoie UNIQUEMENT le texte final nettoyé et corrigé. Ne fais aucune phrase d'introduction ni de conclusion.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Texte à nettoyer :
{safe_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
        messages = [{"role": "user", "content": prompt}]
        # Using a reliable instruction-following model updated for better formatting (Llama-3.1)
        response = client.chat_completion(model="meta-llama/Llama-3.1-8B-Instruct", messages=messages, max_tokens=1500, temperature=0.1)
        return response.choices[0].message.content.strip(), is_truncated
    except Exception as e:
        logger.error(f"Failed to use Hugging Face for correction: {e}")
        raise e
