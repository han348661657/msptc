"""解析槽式光学模型（移植项目8 + EuroTrough IAM）。

η_opt(θ) = ρ·γ·τ·α·cleanliness · K_IAM(θ) · η_end(θ)
余弦投影在 base.absorbed_power_per_length 中以 DNI·cosθ 施加。
IAM: EuroTrough (Geyer 2002), 归一化使 K(0)=1。
"""
import math
from msptc.optics.base import OpticalModel, FluxProfile, DEG


class AnalyticalOptics(OpticalModel):
    def __init__(self, optics_cfg: dict, collector_cfg: dict, receiver_cfg: dict = None,
                 rho_air: float = None, v_wind: float = None, wind_cfg: dict = None):
        o = optics_cfg
        if o.get("intercept_model", "fixed") == "error_cone":
            from msptc.optics.intercept import effective_intercept
            self.intercept = effective_intercept(o, collector_cfg, receiver_cfg,
                                                 rho_air=rho_air, v_wind=v_wind, wind_cfg=wind_cfg)
        else:
            self.intercept = o["intercept"]
        self.peak = (o["reflectance"] * self.intercept * o["transmittance"]
                     * o["absorptance"] * o["cleanliness"])
        self.iam_model = o.get("iam_model", "eurotrough")
        self.aperture_m = collector_cfg["aperture_m"]
        self.focal_m = collector_cfg["focal_m"]
        self.sca_length_m = collector_cfg["sca_length_m"]

    def iam(self, theta_deg: float) -> float:
        """入射角修正因子 K_IAM(θ), K(0)=1。"""
        if theta_deg < 0:
            raise ValueError(f"入射角不能为负: {theta_deg}")
        if theta_deg < 1e-6:
            return 1.0
        th = theta_deg
        cos_t = math.cos(th * DEG)
        if self.iam_model == "eurotrough":
            # K·cosθ = cosθ - 5.25097e-4·θ - 2.859621e-5·θ²  →  K = 1 - (…)/cosθ
            return 1.0 - (5.25097e-4 * th + 2.859621e-5 * th**2) / cos_t
        raise ValueError(f"未知 IAM 模型: {self.iam_model}")

    def end_loss(self, theta_deg: float) -> float:
        return 1.0 - (self.focal_m / self.sca_length_m) * math.tan(theta_deg * DEG)

    def efficiency(self, theta_deg: float) -> float:
        if theta_deg >= 90.0:
            return 0.0
        return max(0.0, self.peak * self.iam(theta_deg) * self.end_loss(theta_deg))

    def flux_on_absorber(self, theta_deg: float, dni: float) -> FluxProfile:
        q = self.absorbed_power_per_length(theta_deg, dni)
        return FluxProfile(peak_w_m=q, mean_w_m=q)
