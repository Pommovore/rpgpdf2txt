from huggingface_hub import InferenceClient
from loguru import logger

from typing import Tuple
import re

# Motifs de préambule courants que le LLM ajoute malgré les instructions
_PREAMBLE_PATTERNS = [
    r"^Voici\s+le\s+texte\s+nettoy[ée].*?[:\n]+\s*",
    r"^Voici\s+la\s+version\s+corrig[ée].*?[:\n]+\s*",
    r"^Voici\s+le\s+texte\s+corrig[ée].*?[:\n]+\s*",
    r"^Voici\s+le\s+résultat.*?[:\n]+\s*",
    r"^Le\s+texte\s+nettoy[ée].*?[:\n]+\s*",
    r"^Texte\s+nettoy[ée]\s*[:\n]+\s*",
]

def _strip_preamble(text: str) -> str:
    """Supprime les phrases d'introduction parasites que le LLM peut ajouter."""
    stripped = text
    for pattern in _PREAMBLE_PATTERNS:
        stripped = re.sub(pattern, "", stripped, count=1, flags=re.IGNORECASE)
    return stripped.strip()

async def correct_text_with_hf(text: str, token: str) -> Tuple[str, bool]:
    """
    Sends the extracted text to a Hugging Face model to correct syntax and spelling errors.
    Splits the text into chunks to bypass token limits, then stitches them back together.
    Returns a tuple (corrected_text, is_truncated).
    """
    try:
        # Using a reliable instruction-following lightweight model
        client = InferenceClient(token=token)
        
        # Chunking the text by lines to respect the ~3000 chars limit per chunk
        max_chunk_size = 3000
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    # A single line is longer than max_chunk_size
                    chunks.append(line[:max_chunk_size])
                    current_chunk = line[max_chunk_size:] + "\n"
            else:
                current_chunk += line + "\n"
                
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        corrected_chunks = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Tu es un assistant expert spécialisé dans le nettoyage de textes extraits par OCR (reconnaissance optique de caractères).
Ta mission est de corriger les fautes d'orthographe et les erreurs de grammaire causées par l'OCR.
DE PLUS, tu dois IMPÉRATIVEMENT nettoyer le texte en supprimant :
- Les numéros de page
- Les en-têtes (headers) et pieds de page (footers)
- Les artefacts de mise en page, les caractères parasites et les "décorateurs"

Conserve l'intégralité du texte principal sans en modifier le sens.
Renvoie UNIQUEMENT le texte final nettoyé et corrigé.
NE COMMENCE PAS ta réponse par une phrase comme "Voici le texte" ou "Voici la version corrigée".
Commence DIRECTEMENT par le premier mot du texte corrigé, sans aucune introduction ni conclusion.
<|eot_id|><|start_header_id|>user<|end_header_id|>
Texte à nettoyer (partie {i+1}/{len(chunks)}) :
{chunk}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
            messages = [{"role": "user", "content": prompt}]
            
            try:
                # Synchronous call; in an async heavy-load server, this might block. 
                # For an internal/admin script, it is fine to run sequentially.
                response = client.chat_completion(
                    model="meta-llama/Llama-3.1-8B-Instruct", 
                    messages=messages, 
                    max_tokens=1500, 
                    temperature=0.1
                )
                corrected_text = response.choices[0].message.content.strip()
                corrected_text = _strip_preamble(corrected_text)
                corrected_chunks.append(corrected_text)
            except Exception as e:
                logger.error(f"Failed to correct chunk {i+1}: {e}")
                # Fallback: keep the original chunk if correction fails to avoid losing data
                corrected_chunks.append(chunk)
                
        # Join all corrected chunks
        final_text = "\n\n".join(corrected_chunks)
        
        # is_truncated is now always False since we process everything in chunks
        return final_text, False
    except Exception as e:
        logger.error(f"Failed to use Hugging Face for correction: {e}")
        raise e
