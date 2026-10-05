"""Pinned neural model identities and preprocessing shared with the local worker."""

TEXT_MODEL = "BAAI/bge-small-zh-v1.5"
TEXT_REVISION = "7999e1d3359715c523056ef9478215996d62a620"
CLIP_MODEL = "OFA-Sys/chinese-clip-vit-base-patch16"
CLIP_REVISION = "36e679e65c2a2fead755ae21162091293ad37834"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
TEXT_CONTRACT = "bge-cls+l2+max512+query-instruction-only+transformers4.51.3-v1"
IMAGE_CONTRACT = (
    "chinese-clip-rgb+transport-thumbnail1536-lanczos+processor224"
    "+projection+l2+transformers4.51.3-v1"
)
CLIP_TEXT_CONTRACT = "chinese-clip-tokenizer+max52+text-projection+l2+transformers4.51.3-v1"

MODEL_SPECS = {
    "text": {
        "provider": "bge_zh",
        "model": TEXT_MODEL,
        "version": TEXT_REVISION,
        "dimension": 512,
        "contract": TEXT_CONTRACT,
    },
    "image": {
        "provider": "chinese_clip_image",
        "model": CLIP_MODEL,
        "version": CLIP_REVISION,
        "dimension": 512,
        "contract": IMAGE_CONTRACT,
    },
    "clip_text": {
        "provider": "chinese_clip_text",
        "model": CLIP_MODEL,
        "version": CLIP_REVISION,
        "dimension": 512,
        "contract": CLIP_TEXT_CONTRACT,
    },
}
