"""
app.py — Streamlit UI for the Satellite Link Quality Simulator
==============================================================
All physics are delegated to satellite_link_sim.simulate_station().

UI controls fall into three groups:

  RF / link layer  : carrier frequency, polarization, bandwidth,
                     EIRP offset (power amplifier headroom)
  Environment      : weather mode, rain intensity scale
  Simulation       : window length, network load (ML feature)

ML feature vector (matches trained scaler/model schema):
  snr_db      ← r.snr_mean   (avg SNR across simulation window)
  packet_loss ← r.avg_pkt_loss
  load_factor ← user slider
"""

import streamlit as st
import pandas as pd
import joblib

from ground_stations import GROUND_STATIONS
from satellite_link_sim import (
    simulate_station, StationResult,
    DEFAULT_CARRIER_FREQ_HZ, DEFAULT_BANDWIDTH_HZ, DEFAULT_POLARIZATION,
    DEFAULT_N_STEPS, SNR_THRESHOLD_DB,
)

# ── ML assets ─────────────────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    return joblib.load("xgb_link_model.pkl"), joblib.load("feature_scaler.pkl")

model, scaler = load_model()

FEATURE_COLS = ["snr_db", "packet_loss", "load_factor"]

def build_features(r: StationResult, load: float) -> pd.DataFrame:
    return pd.DataFrame(
        [[r.snr_mean, r.avg_pkt_loss, load]],
        columns=FEATURE_COLS,
    )

def score_station(r: StationResult, load: float) -> float:
    return float(model.predict(scaler.transform(build_features(r, load)))[0])


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Satellite Link Simulator", layout="wide")
st.title("Multi-Ground-Station Link Quality Simulator")
st.caption(
    "Physics: ITU-R P.837 / P.838 / P.839 / P.618 / P.676 / P.1853  "
    "·  ML scorer: XGBoost"
)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Sidebar — all user controls                                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with st.sidebar:
    st.header("RF / Link layer")

    freq_ghz = st.slider(
        "Carrier frequency (GHz)",
        min_value=10.0, max_value=30.0, value=14.0, step=0.5,
        help="Changes FSPL (+20 dB/decade), P.838 k/α coefficients, and gaseous absorption.",
    )

    polarization = st.radio(
        "Polarization",
        ["vertical", "horizontal"],
        help="Switches ITU-R P.838 k/α coefficients. "
             "Horizontal polarization has higher rain attenuation.",
    )

    bw_mhz = st.slider(
        "Transponder bandwidth (MHz)",
        min_value=18, max_value=72, value=36, step=9,
        help="Wider bandwidth raises the thermal noise floor (kTB), reducing SNR.",
    )

    eirp_offset = st.slider(
        "EIRP offset (dB)",
        min_value=-10.0, max_value=10.0, value=0.0, step=0.5,
        help="Simulates power amplifier headroom (+) or deliberate power reduction (−). "
             "Applied on top of each station's rated EIRP.",
    )

    st.divider()
    st.header("Environment")

    weather = st.radio(
        "Weather mode",
        ["Clear (probabilistic)", "Rain (forced)"],
        help="Clear uses the ITU-R P.837 Markov onset probability. "
             "Rain forces the AR(1) process into its raining state every step.",
    )
    force_rain = weather.startswith("Rain")

    rain_scale = st.slider(
        "Rain intensity scale",
        min_value=0.5, max_value=3.0, value=1.0, step=0.25,
        help="Multiplier on ITU-R P.837-7 rain rates. "
             "1.0 = climatological average. "
             "2.0 = severe event (roughly equivalent to a tropical squall). "
             "Only affects results when rain is active.",
        disabled=not force_rain,
    )

    st.divider()
    st.header("Simulation")

    n_steps = st.slider(
        "Window (minutes)", min_value=10, max_value=180, value=60, step=10,
        help="Each step is 60 s. Longer windows average out short rain events.",
    )

    load = st.slider(
        "Network load", min_value=0.0, max_value=1.0, value=0.4, step=0.05,
        help="Fraction of link capacity in use — fed directly to the ML model.",
    )

    st.divider()
    st.caption(f"Outage threshold: SNR < {SNR_THRESHOLD_DB:.0f} dB  "
               f"(Ku-band DVB-S2 practical floor)")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Run simulation                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@st.cache_data(show_spinner="Running ITU-R physics simulation…")
def run_all(n_steps, force_rain, freq_hz, polarization,
            bandwidth_hz, eirp_offset_db, rain_rate_scale):
    """
    Cache key covers every physical parameter that changes simulation output.
    Changing only 'load' re-scores without re-simulating.
    """
    out = []
    for gs in GROUND_STATIONS:
        r = simulate_station(
            gs,
            n_steps         = n_steps,
            force_rain      = force_rain,
            seed            = hash(gs["name"]) % 100_000,
            freq_hz         = freq_hz,
            eirp_offset_db  = eirp_offset_db,
            bandwidth_hz    = bandwidth_hz,
            polarization    = polarization,
            rain_rate_scale = rain_rate_scale,
        )
        out.append((gs, r))
    return out

sim_results = run_all(
    n_steps         = n_steps,
    force_rain      = force_rain,
    freq_hz         = freq_ghz * 1e9,
    polarization    = polarization,
    bandwidth_hz    = bw_mhz * 1e6,
    eirp_offset_db  = eirp_offset,
    rain_rate_scale = rain_scale if force_rain else 1.0,
)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Score and build display table                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

rows = []
for gs, r in sim_results:
    score = score_station(r, load)
    rows.append({
        "Station":             r.name,
        "Elevation (°)":       round(r.elevation, 1),
        "Slant range (km)":    round(r.slant_km, 0),
        "FSPL (dB)":           round(r.path_loss, 2),
        "Gas loss (dB)":       round(r.gas_loss, 3),
        "Eff. rain path (km)": round(r.eff_path, 2),
        "SNR mean (dB)":       round(r.snr_mean, 2),
        "SNR p10 (dB)":        round(r.snr_p10, 2),
        "SNR std (dB)":        round(r.snr_std, 3),
        "Rain fraction (%)":   round(r.rain_fraction * 100, 1),
        "Avg rain atten (dB)": round(r.avg_rain_db, 2),
        "Outage (%)":          round(r.outage_fraction * 100, 1),
        "Avg pkt loss":        round(r.avg_pkt_loss, 4),
        "Link quality":        round(score, 3),
        "_result":             r,
    })

df_full    = pd.DataFrame(rows).sort_values("Link quality", ascending=False)
df_display = df_full.drop(columns=["_result"]).reset_index(drop=True)
best       = df_full.iloc[0]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Summary metrics row                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Best station",    best["Station"])
c2.metric("Link quality",    f"{best['Link quality']:.3f}")
c3.metric("SNR mean",        f"{best['SNR mean (dB)']:.1f} dB")
c4.metric("SNR p10",         f"{best['SNR p10 (dB)']:.1f} dB")
c5.metric("Outage",          f"{best['Outage (%)']:.1f} %")

st.divider()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Ranked table                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

st.subheader("Station ranking")
st.dataframe(
    df_display.style
        .background_gradient(subset=["Link quality"],        cmap="RdYlGn")
        .background_gradient(subset=["SNR mean (dB)"],       cmap="RdYlGn")
        .background_gradient(subset=["Outage (%)"],          cmap="RdYlGn_r")
        .background_gradient(subset=["Avg rain atten (dB)"], cmap="RdYlGn_r")
        .format(precision=2),
    use_container_width=True,
    hide_index=True,
)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Time series charts                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

tab_snr, tab_rain, tab_pkt = st.tabs(["SNR time series", "Rain attenuation", "Packet loss"])

with tab_snr:
    snr_df = pd.DataFrame(
        {row["Station"]: row["_result"].snr_series for _, row in df_full.iterrows()}
    )
    snr_df.index.name = "Step (min)"
    st.line_chart(snr_df, use_container_width=True)
    st.caption(f"Dashed reference: outage threshold = {SNR_THRESHOLD_DB} dB")

with tab_rain:
    rain_df = pd.DataFrame(
        {row["Station"]: row["_result"].rain_db_series for _, row in df_full.iterrows()}
    )
    rain_df.index.name = "Step (min)"
    st.line_chart(rain_df, use_container_width=True)
    st.caption("ITU-R P.838-3: A = k · R^α · L_eff  [dB]")

with tab_pkt:
    pkt_df = pd.DataFrame(
        {row["Station"]: row["_result"].pkt_loss_series for _, row in df_full.iterrows()}
    )
    pkt_df.index.name = "Step (min)"
    st.line_chart(pkt_df, use_container_width=True)
    st.caption(f"Sigmoid centred at SNR threshold ({SNR_THRESHOLD_DB} dB)")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Per-station physics breakdown (expandable)                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

st.subheader("Per-station physics breakdown")

for _, row in df_full.iterrows():
    r: StationResult = row["_result"]
    with st.expander(
        f"{r.name}  —  quality {row['Link quality']:.3f}  "
        f"|  SNR mean {r.snr_mean:.1f} dB  |  outage {r.outage_fraction*100:.0f}%"
    ):
        col_geo, col_prop, col_rain, col_stat = st.columns(4)

        with col_geo:
            st.markdown("**Geometry**")
            st.metric("Elevation",     f"{r.elevation:.1f} °")
            st.metric("Slant range",   f"{r.slant_km:.0f} km")
            st.metric("Doppler shift", f"{r.doppler_hz:+.0f} Hz")

        with col_prop:
            st.markdown("**Propagation**")
            st.metric("FSPL",           f"{r.path_loss:.2f} dB")
            st.metric("Gas absorption", f"{r.gas_loss:.3f} dB")
            st.metric("Noise floor",    f"{r.noise_floor:.1f} dBW")

        with col_rain:
            st.markdown("**Rain (ITU-R P.838)**")
            st.metric("Rain height",    f"{r.rain_height:.2f} km")
            st.metric("Eff. path",      f"{r.eff_path:.2f} km")
            st.metric("k / α",          f"{r.itu_k:.4f} / {r.itu_alpha:.3f}")
            st.metric("Scint. σ",       f"{r.scint_sig:.4f} dB")

        with col_stat:
            st.markdown("**Link statistics**")
            st.metric("SNR mean",  f"{r.snr_mean:.2f} dB")
            st.metric("SNR p10",   f"{r.snr_p10:.2f} dB")
            st.metric("SNR std",   f"{r.snr_std:.3f} dB")
            st.metric("Pkt loss",  f"{r.avg_pkt_loss:.4f}")

        st.line_chart(
            pd.DataFrame({
                "SNR (dB)":           r.snr_series,
                "Rain atten (dB)":    r.rain_db_series,
            }),
            use_container_width=True,
        )

        st.caption("ML feature vector sent to XGBoost:")
        st.dataframe(build_features(r, load), use_container_width=True, hide_index=True)
