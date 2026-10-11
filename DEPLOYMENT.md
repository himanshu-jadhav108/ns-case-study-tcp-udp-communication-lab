# Deployment Checklist — Streamlit Community Cloud

Reference: https://docs.streamlit.io/deploy/streamlit-community-cloud

---

## Required files

| File | Purpose |
|---|---|
| `app.py` | **Entry point** — Streamlit dashboard |
| `simulator.py` | Network-condition simulator (imported by `app.py`) |
| `requirements.txt` | Python dependency list |
| `.streamlit/config.toml` | Streamlit theme and server settings |
| `local_lab/` | Real-socket lab scripts (not started by cloud) |
| `tests/` | Automated test suite |

---

## Python & dependency requirements

- **Python:** 3.10 or newer (Community Cloud provides 3.12 by default).
- **Streamlit:** `>=1.37, <2`
- **pandas:** `>=2.0, <4`
- No other third-party packages are required.

---

## Repository preparation

```bash
# From the project root
git init
git add app.py simulator.py requirements.txt README.md DEPLOYMENT.md \
        .gitignore .streamlit local_lab tests
git commit -m "Initial: TCP/UDP Communication Lab"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

**Do NOT commit:**
- `.venv/` or `venv/` — add to `.gitignore`
- `local_lab/received_files/` — add to `.gitignore`
- `local_lab/local_observations.csv` — add to `.gitignore`
- Any `*.pyc` / `__pycache__` — add to `.gitignore`
- API keys, credentials, or secrets of any kind

---

## Secrets configuration

**No secrets are required.** The dashboard uses no external APIs or credentials.

If you add features that require secrets in future, configure them via:
- Streamlit Cloud UI → App settings → **Secrets**
- Format: TOML, e.g. `MY_KEY = "value"`
- Access in code: `st.secrets["MY_KEY"]`

Never hardcode secrets in source files.

---

## Streamlit Community Cloud setup

1. Log in at [share.streamlit.io](https://share.streamlit.io).
2. Click **Create app**.
3. Select **From an existing repository**.
4. Fill in:
   - **Repository:** `YOUR-USERNAME/YOUR-REPO`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **Deploy**.
6. The platform installs `requirements.txt` and launches the dashboard.
7. Verify that the yellow cloud notice banner is visible and simulator outputs are labelled SIMULATED.

> **Do not** configure a startup command that launches `local_lab/server.py`. The server is for local use only.

---

## Verification after deployment

- [ ] App loads without errors.
- [ ] All six tabs are accessible and render correctly.
- [ ] Cloud notice warning is visible.
- [ ] Network Simulator tab produces metrics and charts.
- [ ] CSV download works.
- [ ] Interactive sliders (Flow & Congestion, Simulator) update results.

---

## Known limitations & troubleshooting

| Limitation | Notes |
|---|---|
| No inbound TCP/UDP ports | Expected. The cloud dashboard is simulation-only. |
| No file persistence | `received_files/` and `local_observations.csv` are local-only. |
| Free tier memory | Simulator runs within stdlib + pandas; no large model downloads. |
| Font loading | Custom fonts load from Google Fonts CDN; offline browsers may fall back. |

### Common issues

**App fails to start with `ModuleNotFoundError: simulator`**
→ Ensure `simulator.py` is in the repository root alongside `app.py`.

**`ModuleNotFoundError: local_lab`**
→ The `local_lab/` directory must be present in the repo (tests import from it).

**Charts not rendering**
→ Confirm `pandas>=2.0` is listed in `requirements.txt` with no syntax errors.

**Slow first load**
→ Normal — Community Cloud installs dependencies on first deploy. Subsequent loads use cache.
