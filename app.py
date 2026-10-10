"""TCP/UDP Communication Lab — Streamlit dashboard.

Cloud mode: teaching diagrams, interactive controls, and a seeded network-condition
simulator. All generated observations are labelled SIMULATED.

Local mode: separate local_lab scripts provide real socket measurements.
"""
from __future__ import annotations

from datetime import datetime, timezone
import io

import pandas as pd
import streamlit as st

from simulator import simulate_network, summarize


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TCP/UDP Communication Lab",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Helper ─────────────────────────────────────────────────────────────────────
def _fmt_throughput(bps: float) -> str:
    """Format throughput bytes/s into a human-readable string."""
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.2f} MB/s"
    if bps >= 1_000:
        return f"{bps / 1_000:.1f} KB/s"
    return f"{bps:.0f} B/s"


# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.lab-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0d2137 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(56, 189, 248, 0.15);
    position: relative;
    overflow: hidden;
}
.lab-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(56,189,248,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.lab-title {
    font-size: 1.9rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
}
.lab-subtitle {
    font-size: 0.92rem;
    color: #94a3b8;
    margin: 0;
    font-weight: 400;
}
.badge {
    display: inline-block;
    background: rgba(56,189,248,0.12);
    color: #38bdf8;
    border: 1px solid rgba(56,189,248,0.25);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-top: 0.75rem;
}

.section-heading {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 0.25rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.section-desc {
    font-size: 0.875rem;
    color: #94a3b8;
    margin: 0 0 1.25rem 0;
}

.concept-card {
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.85rem;
}
.concept-card-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
}
.concept-card-body {
    font-size: 0.9rem;
    color: #cbd5e1;
    line-height: 1.6;
}

.metric-row {
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    text-align: center;
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.3rem;
}
.metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f1f5f9;
}
.metric-value.good { color: #4ade80; }
.metric-value.warn { color: #fbbf24; }
.metric-value.bad  { color: #f87171; }

.sim-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.25);
    color: #fbbf24;
    border-radius: 6px;
    padding: 0.3rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}

code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82em;
    background: rgba(15,23,42,0.7);
    border-radius: 4px;
    padding: 0.1em 0.35em;
    color: #7dd3fc;
}

.step-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid rgba(56,189,248,0.2);
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    text-align: center;
    margin-bottom: 1rem;
}
.step-flag {
    font-size: 2rem;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.4rem;
}
.step-direction {
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 500;
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.step-explanation {
    font-size: 0.88rem;
    color: #94a3b8;
    line-height: 1.55;
}

.warning-banner {
    background: rgba(251,191,36,0.08);
    border: 1px solid rgba(251,191,36,0.2);
    border-radius: 10px;
    padding: 0.75rem 1.1rem;
    color: #fbbf24;
    font-size: 0.865rem;
    margin-bottom: 1.25rem;
    line-height: 1.5;
}

.info-highlight {
    background: rgba(56,189,248,0.07);
    border-left: 3px solid #38bdf8;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    color: #cbd5e1;
    font-size: 0.875rem;
    line-height: 1.55;
    margin: 0.75rem 0;
}

.progress-label {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.35rem;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="lab-header">
  <p class="lab-title">🌐 TCP / UDP Communication Lab</p>
  <p class="lab-subtitle">Network &amp; Security — Unit 3 &nbsp;·&nbsp; Pune college learning prototype</p>
  <span class="badge">Interactive Learning Dashboard</span>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="warning-banner">
⚠️ <strong>Cloud notice:</strong> Dashboard results are <strong>simulated</strong>.
Streamlit Community Cloud does not provide inbound arbitrary TCP/UDP socket access.
Run the separate <code>local_lab</code> scripts on your laptop for real socket measurements.
</div>
""",
    unsafe_allow_html=True,
)


# ── Tabs ───────────────────────────────────────────────────────────────────────
overview, handshake, compare, control, simulator_tab, local = st.tabs(
    ["📋 Overview", "🤝 TCP Handshake", "⚖️ TCP vs UDP", "📊 Flow & Congestion", "🔬 Simulator", "💻 Local Lab"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with overview:
    st.markdown('<p class="section-heading">Two complementary modes</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-desc">This lab has a cloud simulation mode and a real-socket local mode. '
        "Neither replaces the other — use both for a complete picture.</p>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        st.markdown(
            """
<div class="concept-card">
  <div class="concept-card-title">☁️ Cloud Simulation Mode</div>
  <div class="concept-card-body">
    Teaching diagrams, interactive controls, and a seeded network-condition simulator.
    Every generated observation is labelled <strong>SIMULATED</strong> and can be
    downloaded as a CSV for your observation record.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            """
<div class="concept-card">
  <div class="concept-card-title">🖥️ Local Real-Socket Lab</div>
  <div class="concept-card-body">
    Run the TCP/UDP server and client on your laptop (or two devices on one trusted
    private network). Local results are labelled <code>local_measured</code> and
    exported to CSV with full timing metadata.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        """
<div class="info-highlight">
  <strong>Why two transports?</strong>&nbsp; TCP is used for messages and files when ordered, reliable
  delivery matters. UDP is used for low-overhead notifications when low delay matters and an
  occasional missing notification can be tolerated.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("#### System architecture")
    st.code(
        """\
Browser / Streamlit Cloud
  └─▶ Python simulator  ──▶  Downloadable simulated observations CSV

Local Python client  ──TCP :5050──▶  Local server  ──▶  received_files/
                     ──UDP :5051──▶                 ──▶  local event output
""",
        language="text",
    )

    st.markdown(
        """
<div class="info-highlight">
  <strong>Ports &amp; multiplexing:</strong> An IP address identifies a host; the transport
  protocol + port selects the receiving service. TCP port <code>5050</code> and UDP port
  <code>5051</code> are configurable examples. The OS demultiplexes arriving segments using
  protocol and destination IP/port (plus connection details for TCP) to select a socket.
</div>
""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TCP HANDSHAKE
# ══════════════════════════════════════════════════════════════════════════════
with handshake:
    st.markdown('<p class="section-heading">TCP three-way handshake</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-desc">Step through each segment exchanged during connection setup.</p>',
        unsafe_allow_html=True,
    )

    step = st.radio(
        "Select handshake step",
        ["1 · SYN", "2 · SYN-ACK", "3 · ACK"],
        horizontal=True,
        key="handshake",
        label_visibility="collapsed",
    )

    descriptions = {
        "1 · SYN": (
            "Client → Server",
            "SYN",
            "The client requests a connection and proposes its initial sequence number (ISN).",
            "#38bdf8",
        ),
        "2 · SYN-ACK": (
            "Server → Client",
            "SYN + ACK",
            "The server acknowledges the client's sequence number and proposes its own ISN.",
            "#818cf8",
        ),
        "3 · ACK": (
            "Client → Server",
            "ACK",
            "The client acknowledges the server's sequence number. Both endpoints can now exchange application data.",
            "#4ade80",
        ),
    }

    sender, flag, explanation, color = descriptions[step]

    st.markdown(
        f"""
<div class="step-card">
  <div class="step-direction">{sender}</div>
  <div class="step-flag" style="color:{color}">{flag}</div>
  <div class="step-explanation">{explanation}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("#### Sequence number exchange")

    seq_col1, seq_col2, seq_col3 = st.columns(3, gap="small")
    with seq_col1:
        st.markdown(
            """
<div class="metric-row">
  <div class="metric-label">Step 1</div>
  <div class="metric-value" style="font-size:1rem;font-family:'JetBrains Mono',monospace;color:#38bdf8">SYN(x)</div>
  <div class="metric-label" style="margin-top:0.3rem">Client proposes ISN x</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with seq_col2:
        st.markdown(
            """
<div class="metric-row">
  <div class="metric-label">Step 2</div>
  <div class="metric-value" style="font-size:0.95rem;font-family:'JetBrains Mono',monospace;color:#818cf8">SYN-ACK(y, ack=x+1)</div>
  <div class="metric-label" style="margin-top:0.3rem">Server proposes ISN y, acks client</div>
</div>
""",
            unsafe_allow_html=True,
        )
    with seq_col3:
        st.markdown(
            """
<div class="metric-row">
  <div class="metric-label">Step 3</div>
  <div class="metric-value" style="font-size:1rem;font-family:'JetBrains Mono',monospace;color:#4ade80">ACK(ack=y+1)</div>
  <div class="metric-label" style="margin-top:0.3rem">Client acks server — connection open</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        """
<div class="info-highlight" style="margin-top:1rem">
  <strong>Local capture note:</strong> In local mode, Wireshark can observe the OS-managed
  handshake on the loopback or LAN interface where capture support permits. The view above
  is a teaching diagram, not a packet capture.
</div>
""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TCP vs UDP COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
with compare:
    st.markdown('<p class="section-heading">Transport protocol comparison</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-desc">Key differences between TCP and UDP across five dimensions.</p>',
        unsafe_allow_html=True,
    )

    comparison_df = pd.DataFrame(
        [
            {
                "Property": "Connection setup",
                "TCP": "Connection-oriented; requires three-way handshake",
                "UDP": "Connectionless; no transport handshake",
            },
            {
                "Property": "Ordering / reliability",
                "TCP": "Ordered byte stream; retransmits lost data",
                "UDP": "Datagrams may be lost, duplicated, or reordered",
            },
            {
                "Property": "Flow / congestion control",
                "TCP": "Provided by the operating system TCP stack",
                "UDP": "Not provided by UDP itself",
            },
            {
                "Property": "Typical lab use",
                "TCP": "Files and reliable messages",
                "UDP": "Low-overhead notifications / probes",
            },
            {
                "Property": "Addressing",
                "TCP": "Source/destination IP and port pair",
                "UDP": "Source/destination IP and port pair",
            },
        ]
    )

    st.dataframe(
        comparison_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Property": st.column_config.TextColumn("Property", width="medium"),
            "TCP": st.column_config.TextColumn("TCP", width="large"),
            "UDP": st.column_config.TextColumn("UDP", width="large"),
        },
    )

    st.markdown(
        """
<div class="info-highlight">
  <strong>Multiplexing &amp; demultiplexing:</strong> Many applications share a host's network
  interface. The OS demultiplexes arriving segments using the protocol and destination IP/port
  (plus full connection tuple for TCP) to deliver data to the correct socket.
</div>
""",
        unsafe_allow_html=True,
    )

    col_tcp, col_udp = st.columns(2, gap="medium")
    with col_tcp:
        st.markdown(
            """
<div class="concept-card">
  <div class="concept-card-title" style="color:#38bdf8">TCP strengths</div>
  <div class="concept-card-body">
    Reliable, ordered delivery. Built-in flow control via receive window advertisement.
    Congestion control managed by OS. Ideal for file transfer, HTTP, and any application
    where data loss is unacceptable.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with col_udp:
        st.markdown(
            """
<div class="concept-card">
  <div class="concept-card-title" style="color:#818cf8">UDP strengths</div>
  <div class="concept-card-body">
    Minimal overhead. No connection state. Lower latency for applications that can tolerate
    occasional packet loss. Used in DNS, VoIP, video streaming, and real-time gaming where
    a dropped packet is better than a delayed one.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — FLOW & CONGESTION CONTROL
# ══════════════════════════════════════════════════════════════════════════════
with control:
    st.markdown('<p class="section-heading">Flow control and congestion control</p>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="large")

    with c1:
        st.markdown(
            """
<div class="concept-card">
  <div class="concept-card-title">Flow control</div>
  <div class="concept-card-body">
    Protects a slow receiver from being overwhelmed by a fast sender.
    TCP advertises a <strong>receive window (rwnd)</strong> in each ACK segment;
    the sender limits unacknowledged data to at most rwnd bytes.
  </div>
</div>
<div class="concept-card">
  <div class="concept-card-title">Congestion control</div>
  <div class="concept-card-body">
    Responds to network-level congestion using a sender-side
    <strong>congestion window (cwnd)</strong>. Feedback mechanisms (packet loss,
    ECN, delay) trigger cwnd reductions. These algorithms live entirely in the
    OS TCP stack — this Python project does not reimplement them.
  </div>
</div>
<div class="concept-card">
  <div class="concept-card-title">⚠️ Measurement caution</div>
  <div class="concept-card-body">
    A throughput change alone does not prove which algorithm caused it. A local
    Wireshark capture may show window advertisements and retransmissions if the
    OS and interface permit capture.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("#### Interactive teaching illustration")
        queued = st.slider("Queued segments (sender)", 1, 20, 8, key="queued")
        receiver_window = st.slider("Receive window — rwnd (segments)", 1, 20, 4, key="rwnd")
        congestion_window = st.slider("Congestion window — cwnd (segments)", 1, 20, 6, key="cwnd")

        sendable = min(receiver_window, congestion_window, queued)
        fill_ratio = sendable / queued if queued else 0

        val_class = "good" if fill_ratio > 0.6 else "warn" if fill_ratio > 0.3 else "bad"
        st.markdown(
            f"""
<div class="metric-row" style="margin-bottom:0.75rem">
  <div class="metric-label">Segments allowed in flight</div>
  <div class="metric-value {val_class}">{sendable}</div>
  <div class="metric-label" style="margin-top:0.3rem">min(rwnd={receiver_window}, cwnd={congestion_window}, queued={queued})</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.progress(fill_ratio)
        st.markdown(
            f'<p class="progress-label">At most <strong>{sendable}</strong> of <strong>{queued}</strong> '
            "queued segments can be in flight under min(rwnd, cwnd). "
            "<em>Teaching illustration — not a live TCP measurement.</em></p>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — NETWORK SIMULATOR
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _cached_simulate(
    packet_count: int,
    packet_bytes: int,
    base_delay_ms: float,
    loss_pct: float,
    bandwidth_kbps: float,
    seed: int,
) -> tuple[list[dict], dict]:
    observations = simulate_network(
        packet_count=packet_count,
        packet_bytes=packet_bytes,
        base_delay_ms=base_delay_ms,
        loss_probability=loss_pct / 100,
        bandwidth_kbps=bandwidth_kbps,
        seed=seed,
    )
    return observations, summarize(observations, bandwidth_kbps)


with simulator_tab:
    st.markdown('<p class="section-heading">Network-condition simulator</p>', unsafe_allow_html=True)

    st.markdown(
        '<div class="sim-badge">⚠ SIMULATED RESULTS — generated from these settings, '
        "not measurements from your device or network.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### Simulation parameters")
    col_p, col_n, col_b = st.columns(3, gap="medium")

    with col_p:
        st.markdown("**Packet settings**")
        packets = st.slider("Packet count", 10, 500, 100, 10, key="sim_packets")
        packet_bytes = st.number_input(
            "Bytes per packet", min_value=64, max_value=1400, value=512, step=64, key="sim_bytes"
        )

    with col_n:
        st.markdown("**Network impairment**")
        delay = st.slider("One-way delay (ms)", 0, 1000, 30, 5, key="sim_delay")
        loss_pct = st.slider("Packet loss probability (%)", 0, 50, 2, key="sim_loss")

    with col_b:
        st.markdown("**Bandwidth & seed**")
        bandwidth = st.slider("Bandwidth cap (Kbit/s)", 8, 10000, 1000, 8, key="sim_bw")
        seed = st.number_input(
            "Random seed", min_value=0, max_value=2**31 - 1, value=7, key="sim_seed"
        )

    with st.spinner("Running simulation…"):
        observations, summary = _cached_simulate(
            packet_count=packets,
            packet_bytes=int(packet_bytes),
            base_delay_ms=delay,
            loss_pct=loss_pct,
            bandwidth_kbps=bandwidth,
            seed=int(seed),
        )

    st.markdown("#### Results")

    loss_color = "bad" if summary["loss_percent"] > 10 else "warn" if summary["loss_percent"] > 3 else "good"
    rel_color = (
        "good" if summary["reliability_percent"] > 96 else
        "warn" if summary["reliability_percent"] > 85 else
        "bad"
    )
    avg_delay_str = "—" if summary["avg_delay_ms"] is None else f"{summary['avg_delay_ms']:.1f} ms"
    tput_str = _fmt_throughput(summary["throughput_bytes_s"])

    m0, m1, m2, m3, m4 = st.columns(5, gap="small")

    m0.markdown(
        f"""<div class="metric-row">
  <div class="metric-label">Delivered</div>
  <div class="metric-value">{summary['received']} / {summary['sent']}</div>
</div>""",
        unsafe_allow_html=True,
    )
    m1.markdown(
        f"""<div class="metric-row">
  <div class="metric-label">Simulated loss</div>
  <div class="metric-value {loss_color}">{summary['loss_percent']:.1f}%</div>
</div>""",
        unsafe_allow_html=True,
    )
    m2.markdown(
        f"""<div class="metric-row">
  <div class="metric-label">Reliability</div>
  <div class="metric-value {rel_color}">{summary['reliability_percent']:.1f}%</div>
</div>""",
        unsafe_allow_html=True,
    )
    m3.markdown(
        f"""<div class="metric-row">
  <div class="metric-label">Avg delay (one-way model)</div>
  <div class="metric-value">{avg_delay_str}</div>
</div>""",
        unsafe_allow_html=True,
    )
    m4.markdown(
        f"""<div class="metric-row">
  <div class="metric-label">Simulated throughput</div>
  <div class="metric-value">{tput_str}</div>
</div>""",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    frame = pd.DataFrame(observations)

    chart_col1, chart_col2 = st.columns(2, gap="medium")

    with chart_col1:
        st.markdown("**Per-packet delay (one-way model, ms)**")
        st.line_chart(
            frame.set_index("sequence")[["delay_ms"]],
            use_container_width=True,
            height=260,
            color="#38bdf8",
        )
        st.caption(
            "Simulated one-way delay values. Local client measurements use RTT "
            "unless synchronized clocks permit one-way delay."
        )

    with chart_col2:
        st.markdown("**Packet loss by sequence number**")
        loss_series = frame.assign(lost=(~frame["delivered"]).astype(int)).set_index("sequence")["lost"]
        st.bar_chart(
            loss_series,
            use_container_width=True,
            height=260,
            color="#f87171",
        )
        st.caption(
            "1 = packet not delivered in simulation. Loss is randomly seeded and reproducible per seed value."
        )

    output = io.StringIO()
    csv_frame = frame.copy()
    csv_frame.insert(0, "timestamp_utc", datetime.now(timezone.utc).isoformat())
    csv_frame["protocol"] = "UDP-like simulator"
    csv_frame["condition_delay_ms"] = delay
    csv_frame["condition_loss_probability"] = loss_pct / 100
    csv_frame["condition_bandwidth_kbps"] = bandwidth
    csv_frame.to_csv(output, index=False)

    st.download_button(
        label="⬇ Download simulated observations CSV",
        data=output.getvalue(),
        file_name="simulated_observations.csv",
        mime="text/csv",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — LOCAL LAB INSTRUCTIONS
# ══════════════════════════════════════════════════════════════════════════════
with local:
    st.markdown('<p class="section-heading">Run the real-socket lab locally</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-desc">Step-by-step instructions for launching the TCP/UDP server and client on your machine.</p>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Step 1 — Environment setup")
    st.code(
        """\
# In your project folder (requires Python 3.10+)
python -m venv .venv
.venv\\Scripts\\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate           # macOS / Linux

python -m pip install -r requirements.txt""",
        language="powershell",
    )

    st.markdown("#### Step 2 — Start the server")
    st.code(
        """\
cd local_lab
python server.py
# Server defaults: TCP 127.0.0.1:5050 / UDP 127.0.0.1:5051
# Received files are written to local_lab/received_files/""",
        language="powershell",
    )

    st.markdown("#### Step 3 — Run client commands (second terminal)")
    st.code(
        """\
# Send a TCP message
python client.py message "Hello from the TCP client"

# Transfer a file over TCP (SHA-256 verified, ≤10 MiB)
python client.py file path\\to\\a\\small-file.txt

# Send a UDP notification batch
python client.py udp --count 50 --interval 0.02""",
        language="powershell",
    )

    st.markdown(
        """
<div class="info-highlight">
  <strong>Security notes:</strong> Default bind is loopback (<code>127.0.0.1</code>). Received files
  are written only inside <code>local_lab/received_files/</code> with sanitized names and a 10 MiB
  default limit. Do not execute received files. Stop the server with <code>Ctrl+C</code>.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("#### Optional — Two-device LAN mode")
    st.code(
        """\
# On the server device: find its LAN IP (ipconfig / ip addr), then:
python server.py --host 192.168.1.20   # replace with your server LAN IP

# On the client device:
python client.py --host 192.168.1.20 message "Hello over LAN"
python client.py --host 192.168.1.20 udp --count 50""",
        language="text",
    )

    st.markdown(
        """
<div class="warning-banner">
  <strong>LAN mode caution:</strong> Use only a trusted private network. Allow only TCP 5050 and UDP 5051
  through the host firewall. Remove temporary firewall rules and stop the server after the lab.
  Do not bind to a public interface or expose these ports to the internet.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("#### CSV output format")
    st.markdown(
        "Client commands append real local events to `local_observations.csv` with `mode=local_measured`. "
        "UDP missing echo ACKs indicate possible loss on either direction; RTT is measured, not one-way delay."
    )
    st.code(
        '{"time":"<UTC timestamp>","protocol":"TCP","peer":"<address>",'
        '"message":"file received and verified","bytes":1234,"duration_s":<measured>}',
        language="json",
    )

    st.markdown("#### Reproducible network-condition observations")
    st.markdown(
        "Record a baseline first, then repeat with added latency, restricted bandwidth, and controlled "
        "packet loss. For actual local impairment, use an instructor-approved emulator (e.g. Linux "
        "`tc/netem`) following the instructor's setup and cleanup instructions. "
        "This app **never** changes network settings."
    )
