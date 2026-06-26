"""集热器回路：沿流向分段串联 optics + receiver。"""
from dataclasses import dataclass
from msptc.receiver import hce_steady, ReceiverGeom


@dataclass
class CollectorResult:
    T_out_C: float
    Q_useful_W: float
    Q_loss_W: float
    eta_th: float


class Collector:
    def __init__(self, cfg: dict, optics, htf, air=None, sky_model=None):
        self.optics = optics
        self.htf = htf
        self.air = air
        self.sky_model = sky_model
        self.aperture_m = cfg["collector"]["aperture_m"]
        self.L_total = cfg["collector"]["sca_length_m"] * cfg["collector"]["n_sca"]
        self.default_n_seg = cfg["collector"].get("n_segments", 1)
        r = cfg["receiver"]
        self.geom = ReceiverGeom(
            d_abs_in_m=r["d_abs_in_m"], d_abs_out_m=r["d_abs_out_m"],
            d_glass_in_m=r["d_glass_in_m"], d_glass_out_m=r["d_glass_out_m"],
            eps_abs=r["eps_abs"], eps_glass=r["eps_glass"], vacuum=r["vacuum"],
        )

    def simulate_steady(self, T_in_C, mdot, dni, theta_deg, T_amb_C, wind, n_segments=None):
        n = n_segments or self.default_n_seg
        if n < 1:
            raise ValueError(f"n_segments 必须 >= 1，当前值: {n}")
        if mdot <= 0:
            raise ValueError(f"质量流量 mdot 必须 > 0，当前值: {mdot}")
        L_seg = self.L_total / n
        q_abs_per_m = self.optics.absorbed_power_per_length(theta_deg, dni)
        T = T_in_C
        T_max_htf = getattr(self.htf, 'T_max_C', float('inf'))
        Q_use_tot = 0.0
        Q_loss_tot = 0.0
        for _ in range(n):
            # Predictor: estimate outlet temperature using inlet conditions
            res_in = hce_steady(T, mdot, q_abs_per_m, T_amb_C, wind, self.geom, self.htf,
                                air=self.air, sky_model=self.sky_model)
            T_out_pred = min(T + res_in.q_useful_per_m * L_seg / (mdot * self.htf.cp(T)),
                             T_max_htf)
            # Corrector: evaluate at midpoint temperature for better accuracy
            T_mid = 0.5 * (T + T_out_pred)
            res = hce_steady(T_mid, mdot, q_abs_per_m, T_amb_C, wind, self.geom, self.htf,
                             air=self.air, sky_model=self.sky_model)
            cp_mid = self.htf.cp(T_mid)
            T_new = T + res.q_useful_per_m * L_seg / (mdot * cp_mid)
            if T_new > T_max_htf:
                # Clamp outlet to HTF upper limit; reduce Q_use for energy consistency
                Q_use = (T_max_htf - T) * mdot * cp_mid
                T_new = T_max_htf
            else:
                Q_use = res.q_useful_per_m * L_seg
            Q_use_tot += Q_use
            Q_loss_tot += res.q_loss_per_m * L_seg
            T = T_new
        Q_solar = dni * self.aperture_m * self.L_total
        eta = Q_use_tot / Q_solar if Q_solar > 0 else 0.0
        return CollectorResult(T_out_C=T, Q_useful_W=Q_use_tot, Q_loss_W=Q_loss_tot, eta_th=eta)
