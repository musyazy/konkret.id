# Kalkulator Mix Design Beton (Streamlit)

    pip install -r requirements.txt
    streamlit run app.py

Struktur: `app.py` (UI) · `standards/sni.py`, `standards/aci.py` (logika) · `standards/base.py` (dataclass hasil & interpolasi) · `utils/material_db.py` (data agregat).
Uji cepat logika tanpa UI: `python -c "from standards import sni, aci"`.
