"""
Memory Optimizer Module
Sets up optimal environment variables and configurations to prevent memory issues and semaphore leaks
"""

import os
import gc
import logging

logger = logging.getLogger(__name__)

def setup_memory_optimized_environment():
    """
    Configure environment variables for memory-efficient ML library usage.
    This helps prevent segfaults and semaphore leaks on memory-constrained systems.
    """
    
    # Core memory optimization settings
    env_settings = {
        # Prevent OpenMP library conflicts and excessive threading
        'KMP_DUPLICATE_LIB_OK': 'TRUE',
        'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'VECLIB_MAXIMUM_THREADS': '1',
        
        # PyTorch optimizations for low memory
        'TORCH_NUM_THREADS': '1',
        'PYTORCH_DISABLE_CUBLAS_WORKSPACE': '1',
        
        # Transformers/Tokenizers optimization
        'TOKENIZERS_PARALLELISM': 'false',
        'TRANSFORMERS_OFFLINE': '1',  # Prevent unnecessary downloads
        
        # FAISS optimizations
        'FAISS_NUM_THREADS': '1',
        
        # Memory management for Python
        'MALLOC_TRIM_THRESHOLD_': '100000',
        'MALLOC_MMAP_THRESHOLD_': '100000',
        
        # Disable multiprocessing in various libraries
        'JOBLIB_MULTIPROCESSING': '0',
        'NUMBA_DISABLE_JIT': '1',  # Disable JIT compilation to save memory
        
        # Force single-threaded execution to prevent semaphore leaks
        'PYTHONOPTIMIZE': '1',
        'MULTIPROCESSING_START_METHOD': 'spawn',  # Safer on macOS
        
        # HuggingFace optimizations
        'HF_HOME': '/tmp/huggingface_cache',  # Use tmp for cache
        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
        
        # Set memory limits for sentence-transformers
        'SENTENCE_TRANSFORMERS_HOME': '/tmp/sentence_transformers',
    }
    
    logger.info("🔧 Setting up memory-optimized environment...")
    
    # Setup resource cleanup first to prevent leaks
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))  # Project root
        from cleanup_resources import setup_cleanup_handlers
        setup_cleanup_handlers()
        logger.info("✅ Resource cleanup handlers installed")
    except Exception as e:
        logger.debug(f"Resource cleanup setup failed: {e}")
    
    for key, value in env_settings.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.debug(f"Set {key}={value}")
        else:
            logger.debug(f"{key} already set to {os.environ[key]}")
    
    # Force garbage collection
    gc.collect()
    
    logger.info("✅ Memory optimization environment configured")

def get_memory_conservative_model_config():
    """Get configuration for memory-conservative model loading"""
    return {
        'device': 'cpu',  # Force CPU usage to avoid GPU memory issues
        'torch_dtype': 'float16',  # Use half precision to save memory
        'low_cpu_mem_usage': True,
        'use_cache': False,  # Disable caching to save memory
    }

def check_available_memory():
    """Check available system memory and return recommendation"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        logger.info(f"💾 Available memory: {available_gb:.1f} GB")
        
        if available_gb < 1.0:
            logger.warning("⚠️ Low memory detected - enabling conservative mode")
            return "conservative"
        elif available_gb < 2.0:
            logger.info("ℹ️ Moderate memory available - using balanced mode")
            return "balanced"
        else:
            logger.info("✅ Sufficient memory available - using normal mode")
            return "normal"
            
    except ImportError:
        logger.warning("psutil not available, assuming conservative mode")
        return "conservative"
    except Exception as e:
        logger.error(f"Error checking memory: {e}")
        return "conservative"

def cleanup_memory():
    """Force cleanup of memory and resources"""
    import gc
    
    # Force garbage collection multiple times
    for _ in range(3):
        gc.collect()
    
    # Try to clear ML library caches if available
    try:
        import torch
        if hasattr(torch.cuda, 'empty_cache'):
            torch.cuda.empty_cache()
    except (ImportError, Exception):
        pass
    
    logger.debug("🧹 Memory cleanup completed")

# Setup environment on module import
setup_memory_optimized_environment()
