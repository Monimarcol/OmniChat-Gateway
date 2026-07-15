"""One-shot hardware profiling: CPU, RAM, GPU. Runs synchronously, no polling loop --
hardware doesn't change mid-session, so a single cached scan is enough to keep this
step's own resource footprint near zero after first launch.

Ported from the Kade-AI hardware detection POC.
"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import psutil

CACHE_PATH = Path(__file__).resolve().parent.parent / ".cache" / "hardware_profile.json"
CACHE_TTL_SECONDS = 60 * 60 * 24


@dataclass
class GPUInfo:
    name: str
    vram_gb: Optional[float]
    backend: str  # "cuda", "apple_unified", "integrated", "none"


@dataclass
class HardwareProfile:
    cpu_model: str
    physical_cores: int
    logical_cores: int
    ram_total_gb: float
    ram_available_gb: float
    gpu: GPUInfo
    tier: str
    detected_at: float


def _detect_cpu() -> tuple[str, int, int]:
    try:
        import cpuinfo
        model = cpuinfo.get_cpu_info().get("brand_raw") or platform.processor() or "Unknown CPU"
    except Exception:
        model = platform.processor() or platform.machine() or "Unknown CPU"
    physical = psutil.cpu_count(logical=False) or 1
    logical = psutil.cpu_count(logical=True) or physical
    return model, physical, logical


def _detect_gpu() -> GPUInfo:
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        pynvml.nvmlShutdown()
        return GPUInfo(name=name, vram_gb=round(mem.total / (1024 ** 3), 1), backend="cuda")
    except Exception:
        pass

    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return GPUInfo(name="Apple Silicon (unified memory)", vram_gb=None, backend="apple_unified")

    try:
        if platform.system() == "Windows":
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=3,
            )
            lines = [l.strip() for l in out.stdout.splitlines() if l.strip() and "Name" not in l]
            if lines:
                return GPUInfo(name=lines[0], vram_gb=None, backend="integrated")
        elif platform.system() == "Linux":
            out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
            for line in out.stdout.splitlines():
                if "VGA" in line or "3D" in line:
                    return GPUInfo(name=line.split(":")[-1].strip(), vram_gb=None, backend="integrated")
    except Exception:
        pass

    return GPUInfo(name="No dedicated GPU detected", vram_gb=None, backend="none")


def _classify_tier(ram_total_gb: float, gpu: GPUInfo) -> str:
    has_strong_gpu = gpu.backend == "cuda" and (gpu.vram_gb or 0) >= 8
    has_mid_gpu = gpu.backend in ("cuda", "apple_unified") and (gpu.vram_gb or ram_total_gb) >= 6
    if ram_total_gb >= 32 and has_strong_gpu:
        return "high"
    if ram_total_gb >= 16 and (has_mid_gpu or ram_total_gb >= 24):
        return "mid-high"
    if ram_total_gb >= 8:
        return "mid"
    return "low"


def _run_detection() -> HardwareProfile:
    cpu_model, physical, logical = _detect_cpu()
    vm = psutil.virtual_memory()
    ram_total_gb = round(vm.total / (1024 ** 3), 1)
    ram_available_gb = round(vm.available / (1024 ** 3), 1)
    gpu = _detect_gpu()
    tier = _classify_tier(ram_total_gb, gpu)
    return HardwareProfile(
        cpu_model=cpu_model,
        physical_cores=physical,
        logical_cores=logical,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        gpu=gpu,
        tier=tier,
        detected_at=time.time(),
    )


def get_hardware_profile(force_refresh: bool = False) -> HardwareProfile:
    if not force_refresh and CACHE_PATH.exists():
        try:
            cached = json.loads(CACHE_PATH.read_text())
            if time.time() - cached["detected_at"] < CACHE_TTL_SECONDS:
                cached["gpu"] = GPUInfo(**cached["gpu"])
                return HardwareProfile(**cached)
        except Exception:
            pass

    profile = _run_detection()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(asdict(profile)))
    return profile
