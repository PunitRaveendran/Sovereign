"""Vision model interfaces for the Sovereign multimodal pipeline using llama-server."""

import base64
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional

from app.multimodal.ocr import TesseractOCRProcessor


class VisionModel:
    """Base interface for a local vision-language model."""

    name = "vision_model"

    def process(self, image_path: str, prompt: Optional[str] = None) -> str:
        raise NotImplementedError


class QwenVisionModel(VisionModel):
    """Real Vision Model adapter communicating with our unified llama-server instance.
    
    Eliminates Ollama daemon dependencies and routes all visual inference
    through localhost:8080.
    """

    name = "qwen2.5-vl"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model_name: str = "local-model",
        ocr_fallback: Optional[TesseractOCRProcessor] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.ocr = ocr_fallback or TesseractOCRProcessor()

    def process(
        self,
        image_path: str,
        prompt: Optional[str] = None,
    ) -> str:
        """Process an image using llama-server vision or visual-feature extraction."""
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if prompt is None:
            prompt = "Analyze this industrial equipment inspection image, noting any wear, corrosion, defects, or specifications."

        # Read and encode image to base64
        with open(str(path), "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")

        suffix = path.suffix.lower().replace(".", "")
        mime_type = f"image/{suffix}" if suffix in ["png", "jpeg", "jpg", "webp"] else "image/png"
        data_uri = f"data:{mime_type};base64,{b64_image}"

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "max_tokens": 300,
        }

        # Attempt native multimodal inference via llama-server
        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                if res.getcode() == 200:
                    resp_data = json.loads(res.read().decode("utf-8"))
                    content = resp_data["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content.strip()
        except Exception:
            pass

        # If llama-server lacks an active --mmproj projector, ground visual text via OCR
        extracted_text = self.ocr.extract_text(str(path))
        
        # If no optical text could be extracted, return explicit notification
        if "[OCR_EXTRACTION_UNAVAILABLE" in extracted_text:
            return f"[Vision & OCR Alert: No machine-readable text or telemetry detected in {path.name}. Manual visual inspection required.]"

        grounded_prompt = (
            f"You are the Sovereign Vision Engine analyzing equipment visual scan '{path.name}'.\n"
            f"Extracted markings/telemetry from image:\n{extracted_text}\n\n"
            f"User inspection prompt: {prompt}\n\n"
            f"CRITICAL: Base your analysis STRICTLY on the extracted markings above. "
            f"Do NOT invent numbers or tolerances. "
            f"Provide a brief structured summary of the findings and compliance status."
        )

        text_payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a concise industrial inspection specialist. Deliver direct structured findings."},
                {"role": "user", "content": grounded_prompt}
            ],
            "max_tokens": 600,
            "temperature": 0.1,
        }

        import re
        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(text_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as res:
                resp_data = json.loads(res.read().decode("utf-8"))
                raw_analysis = resp_data["choices"][0]["message"]["content"].strip()
                # Strip think tags if present (both closed and unclosed)
                clean_analysis = re.sub(r'<think>.*?</think>', '', raw_analysis, flags=re.DOTALL).strip()
                if "<think>" in clean_analysis and "</think>" not in clean_analysis:
                    clean_analysis = re.sub(r'<think>.*', '', clean_analysis, flags=re.DOTALL).strip()
                if not clean_analysis:
                    clean_analysis = raw_analysis
                return f"[Raw Optical Telemetry Extracted from Image]:\n{extracted_text}\n\n[Vision Model Technical Assessment]:\n{clean_analysis}"
        except Exception:
            return f"[Raw Optical Telemetry Extracted from Image]:\n{extracted_text}"
