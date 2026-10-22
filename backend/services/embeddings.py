"""
Sentence embeddings with all-MiniLM-L6-v2 on ONNX Runtime.

Uses the same model files as Chroma's DefaultEmbeddingFunction, with two changes found by profiling
(loadtest/profile_retrieval.py):
  - Dynamic padding: the stock function pads every input to 256 tokens, so embedding a 10-token question
    costs as much as a 256-token passage. Padding to the longest text in the batch gives identical
    vectors (padded positions are masked out of attention and pooling) at a fraction of the cost.
  - A bounded thread pool per inference, so concurrent requests don't oversubscribe the CPU.
"""
import os
import threading
from functools import cache

import numpy as np
import onnxruntime as ort
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
from tokenizers import Tokenizer

MAX_TOKENS = 256
BATCH_SIZE = 32


class MiniLMEmbedder:
    def __init__(self, threads: int = 2):
        stock = ONNXMiniLM_L6_V2()
        stock._download_model_if_not_exists()  # reuse Chroma's verified, cached download
        folder = os.path.join(stock.DOWNLOAD_PATH, stock.EXTRACTED_FOLDER_NAME)

        self.tokenizer = Tokenizer.from_file(os.path.join(folder, "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")  # pad to the longest in the batch only
        self._tokenizer_lock = threading.Lock()  # the tokenizer's padding state is shared

        options = ort.SessionOptions()
        options.log_severity_level = 3
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            os.path.join(folder, "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"]
        )

    def __call__(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), BATCH_SIZE):
            with self._tokenizer_lock:
                encoded = self.tokenizer.encode_batch(texts[start:start + BATCH_SIZE])
            ids = np.array([e.ids for e in encoded], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            hidden = self.session.run(
                None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)}
            )[0]
            weights = mask[:, :, None].astype(np.float32)
            pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            vectors.append(pooled / np.clip(norms, 1e-12, None))
        return np.concatenate(vectors).astype(np.float32).tolist() if vectors else []


@cache
def embedder(threads: int = 2) -> MiniLMEmbedder:
    return MiniLMEmbedder(threads)
