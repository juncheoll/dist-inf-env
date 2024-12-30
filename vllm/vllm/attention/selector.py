import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, Optional, Type

import torch

import vllm.envs as envs
from vllm.attention.backends.abstract import AttentionBackend
from vllm.logger import init_logger
from vllm.platforms import _Backend, current_platform
from vllm.utils import STR_BACKEND_ENV_VAR

logger = init_logger(__name__)


def backend_name_to_enum(backend_name: str) -> _Backend:
    assert backend_name is not None

    backend_members = _Backend.__members__
    if backend_name not in backend_members:
        raise ValueError(f"Invalid attention backend '{backend_name}'. "
                         f"Available backends: {', '.join(backend_members)} "
                         "(case-sensitive).")

    return _Backend[backend_name]


def get_env_variable_attn_backend() -> Optional[_Backend]:
    '''
    Get the backend override specified by the vLLM attention
    backend environment variable, if one is specified.

    Returns:

    * _Backend enum value if an override is specified
    * None otherwise
    '''
    backend_name = os.environ.get(STR_BACKEND_ENV_VAR)
    return (None
            if backend_name is None else backend_name_to_enum(backend_name))


# Global state allows a particular choice of backend
# to be forced, overriding the logic which auto-selects
# a backend based on system & workload configuration
# (default behavior if this variable is None)
#
# THIS SELECTION TAKES PRECEDENCE OVER THE
# VLLM ATTENTION BACKEND ENVIRONMENT VARIABLE
forced_attn_backend: Optional[_Backend] = None


def global_force_attn_backend(attn_backend: Optional[_Backend]) -> None:
    '''
    Force all attention operations to use a specified backend.

    Passing `None` for the argument re-enables automatic
    backend selection.,

    Arguments:

    * attn_backend: backend selection (None to revert to auto)
    '''
    global forced_attn_backend
    forced_attn_backend = attn_backend


def get_global_forced_attn_backend() -> Optional[_Backend]:
    '''
    Get the currently-forced choice of attention backend,
    or None if auto-selection is currently enabled.
    '''
    return forced_attn_backend


def get_attn_backend(
    head_size: int,
    dtype: torch.dtype,
    kv_cache_dtype: Optional[str],
    block_size: int,
    is_attention_free: bool,
    is_blocksparse: bool = False,
) -> Type[AttentionBackend]:
    """Selects which attention backend to use and lazily imports it."""
    # Accessing envs.* behind an @lru_cache decorator can cause the wrong
    # value to be returned from the cache if the value changes between calls.
    # To avoid this, we read envs.VLLM_USE_V1 here and pass it explicitly to the
    # private function.
    return _cached_get_attn_backend(
        head_size=head_size,
        dtype=dtype,
        kv_cache_dtype=kv_cache_dtype,
        block_size=block_size,
        is_attention_free=is_attention_free,
        is_blocksparse=is_blocksparse,
        use_v1=envs.VLLM_USE_V1,
    )


@lru_cache(maxsize=None)
def _cached_get_attn_backend(
    head_size: int,
    dtype: torch.dtype,
    kv_cache_dtype: Optional[str],
    block_size: int,
    is_attention_free: bool,
    is_blocksparse: bool = False,
    use_v1: bool = False,
) -> Type[AttentionBackend]:
    if is_blocksparse:
        logger.info("Using BlocksparseFlashAttention backend.")
        from vllm.attention.backends.blocksparse_attn import (
            BlocksparseFlashAttentionBackend)
        return BlocksparseFlashAttentionBackend

    backend = which_attn_to_use(head_size, dtype, kv_cache_dtype, block_size,
                                is_attention_free, use_v1)
    if backend == _Backend.FLASH_ATTN:
        logger.info("Using Flash Attention backend.")
        from vllm.attention.backends.flash_attn import (  # noqa: F401
            FlashAttentionBackend)
        return FlashAttentionBackend
    if backend == _Backend.FLASH_ATTN_VLLM_V1:
        from vllm.v1.attention.backends.flash_attn import (  # noqa: F401
            FlashAttentionBackend as FlashAttentionBackendV1)
        return FlashAttentionBackendV1
    if backend == _Backend.XFORMERS:
        logger.info("Using XFormers backend.")
        from vllm.attention.backends.xformers import (  # noqa: F401
            XFormersBackend)
        return XFormersBackend
    elif backend == _Backend.ROCM_FLASH:
        logger.info("Using ROCmFlashAttention backend.")
        from vllm.attention.backends.rocm_flash_attn import (  # noqa: F401
            ROCmFlashAttentionBackend)
        return ROCmFlashAttentionBackend
    elif backend == _Backend.TORCH_SDPA:
        assert current_platform.is_cpu(), RuntimeError(
            "Torch SDPA backend is only used for the CPU device.")
        logger.info("Using Torch SDPA backend.")
        from vllm.attention.backends.torch_sdpa import TorchSDPABackend
        return TorchSDPABackend
    elif backend == _Backend.OPENVINO:
        logger.info("Using OpenVINO Attention backend.")
        from vllm.attention.backends.openvino import OpenVINOAttentionBackend
        return OpenVINOAttentionBackend
    elif backend == _Backend.IPEX:
        assert current_platform.is_xpu(), RuntimeError(
            "IPEX attention backend is only used for the XPU device.")
        logger.info("Using IPEX attention backend.")
        from vllm.attention.backends.ipex_attn import IpexAttnBackend
        return IpexAttnBackend
    elif backend == _Backend.FLASHINFER:
        logger.info("Using Flashinfer backend.")
        from vllm.attention.backends.flashinfer import FlashInferBackend
        return FlashInferBackend
    elif backend == _Backend.HPU_ATTN:
        logger.info("Using HPUAttention backend.")
        from vllm.attention.backends.hpu_attn import HPUAttentionBackend
        return HPUAttentionBackend
    elif backend == _Backend.PALLAS:
        logger.info("Using Pallas backend.")
        from vllm.attention.backends.pallas import PallasAttentionBackend
        return PallasAttentionBackend
    elif backend == _Backend.NO_ATTENTION:
        from vllm.attention.backends.placeholder_attn import (
            PlaceholderAttentionBackend)
        return PlaceholderAttentionBackend
    else:
        raise ValueError("Invalid attention backend.")


def which_attn_to_use(head_size: int,
                      dtype: torch.dtype,
                      kv_cache_dtype: Optional[str],
                      block_size: int,
                      is_attention_free: bool,
                      use_v1: bool = False) -> _Backend:
    """Returns which flash attention backend to use."""
    # Default case.
    selected_backend = _Backend.FLASH_ATTN

    # If there are no attention layers (e.g. we are running Mamba),
    # use the placeholder NO_ATTENTION
    if is_attention_free:
        return _Backend.NO_ATTENTION

    # Check whether a particular choice of backend was
    # previously forced.
    #
    # THIS SELECTION OVERRIDES THE VLLM_ATTENTION_BACKEND
    # ENVIRONMENT VARIABLE.
    backend_by_global_setting: Optional[_Backend] = (
        get_global_forced_attn_backend())
    if backend_by_global_setting is not None:
        selected_backend = backend_by_global_setting
    else:
        # Check the environment variable and override if specified
        backend_by_env_var: Optional[str] = envs.VLLM_ATTENTION_BACKEND
        if backend_by_env_var is not None:
            selected_backend = backend_name_to_enum(backend_by_env_var)

    # get device-specific default attn_backend
    default_backend = current_platform.get_default_attn_backend(
        selected_backend)
    if default_backend is not None:
        return default_backend

    if use_v1:
        return _Backend.FLASH_ATTN_VLLM_V1

    # FlashAttn in NVIDIA GPUs.
    if selected_backend == _Backend.FLASH_ATTN:
        if not current_platform.has_device_capability(80):
            # Volta and Turing NVIDIA GPUs.
            logger.info(
                "Cannot use FlashAttention-2 backend for Volta and Turing "
                "GPUs.")
            selected_backend = _Backend.XFORMERS
        elif dtype not in (torch.float16, torch.bfloat16):
            logger.info(
                "Cannot use FlashAttention-2 backend for dtype other than "
                "torch.float16 or torch.bfloat16.")
            selected_backend = _Backend.XFORMERS
        elif kv_cache_dtype is not None and kv_cache_dtype.startswith("fp8"):
            logger.info(
                "Cannot use FlashAttention-2 backend for FP8 KV cache.")
            logger.warning(
                "Please use FlashInfer backend with FP8 KV Cache for "
                "better performance by setting environment variable  "
                "VLLM_ATTENTION_BACKEND=FLASHINFER")
            selected_backend = _Backend.XFORMERS
        elif block_size % 16 != 0:
            logger.info(
                "Cannot use FlashAttention-2 backend for block size not "
                "divisible by 16.")
            selected_backend = _Backend.XFORMERS

    # FlashAttn is valid for the model, checking if the package is installed.
    if selected_backend == _Backend.FLASH_ATTN:
        try:
            import vllm.vllm_flash_attn  # noqa: F401
            from vllm.attention.backends.flash_attn import (  # noqa: F401
                FlashAttentionBackend)

            supported_sizes = FlashAttentionBackend.get_supported_head_sizes()
            if head_size not in supported_sizes:
                logger.info(
                    "Cannot use FlashAttention-2 backend for head size %d.",
                    head_size)
                selected_backend = _Backend.XFORMERS
        except ImportError:
            logger.info(
                "Cannot use FlashAttention-2 backend because the "
                "vllm.vllm_flash_attn package is not found. "
                "Make sure that vllm_flash_attn was built and installed "
                "(on by default).")
            selected_backend = _Backend.XFORMERS

    return selected_backend


@contextmanager
def global_force_attn_backend_context_manager(
        attn_backend: _Backend) -> Generator[None, None, None]:
    '''
    Globally force a vLLM attention backend override within a
    context manager, reverting the global attention backend
    override to its prior state upon exiting the context
    manager.

    Arguments:

    * attn_backend: attention backend to force

    Returns:

    * Generator
    '''

    # Save the current state of the global backend override (if any)
    original_value = get_global_forced_attn_backend()

    # Globally force the new backend override
    global_force_attn_backend(attn_backend)

    # Yield control back to the enclosed code block
    try:
        yield
    finally:
        # Revert the original global backend override, if any
        global_force_attn_backend(original_value)