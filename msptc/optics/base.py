"""光学模型抽象接口：解析模型与 SolTrace 适配器实现同一契约。"""
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

DEG = math.pi / 180.0


@dataclass
class FluxProfile:
    peak_w_m: float   # W/m (power per unit axial length of absorber)
    mean_w_m: float   # W/m


class OpticalModel(ABC):
    aperture_m: float  # 子类必须设置

    @abstractmethod
    def efficiency(self, theta_deg: float) -> float:
        """总光学效率 η_opt(θ)（不含余弦投影）。"""

    @abstractmethod
    def flux_on_absorber(self, theta_deg: float, dni: float) -> FluxProfile:
        """吸热管表面通量分布。"""

    def absorbed_power_per_length(self, theta_deg: float, dni: float) -> float:
        """单位长度吸热管吸收太阳功率 (W/m) = DNI·cosθ·孔径·η_opt(θ)。"""
        return dni * math.cos(theta_deg * DEG) * self.aperture_m * self.efficiency(theta_deg)
