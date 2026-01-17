import streamlit as st
import pandas as pd
import copy
from allocation_algo import (
    solve_model,
    run_auto_bid_aggressive,
    calculate_recommendations
)
from products_config import products, SELLER_GLOBAL_MOQ

st.set_page_config(page_title="Allocation Engine – Test UI", layout="wide")

# -----------------------------
# Session State Init
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Helpers
# -----------------------------
def snapshot(label):
    allocations, total_ca = solve_model(st.session_state.buyers, products)
    st.session_state.history.append({
        "label": label,
        "buyers": copy.deepcopy(st.session_state.buyers),
        "allocations": allocations,
        "total_ca": total_ca
    })

def buyers_to_df():
    rows = []
    for b in st.session_state.buyers:
        for pid, p in b["products"].items():
            rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Prix courant": p["current_price"],
                "Prix max": p["max_price"],
                "Qté désirée": p["qty_desired"],
                "MOQ produit": p["moq"],
                "Auto-bid": b.get("auto_bid", False)
            })
    return pd.DataFrame(rows)

# -----------------------------
# Sidebar – Add Buyer
# -----------------------------
st.sidebar.title("➕ Ajouter un acheteur")

with st.sidebar.form("add_buyer"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}
    for p in products:
        st.markdown(f"**{p['name']} ({p['id']})**")
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=p["seller_moq"],  # ⚡ La quantité minimale = MOQ produit
            value=p["seller_moq"],
            step=5
        )
        price = st.number_input(f"Prix courant – {p['id']}", min_value=0.0, value=p["starting_price"])
        max_price_input = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=price
        )
        st.caption(f"Prix suggéré max: {price + 2}")

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price_input,
            "moq": p["seller_moq"]
        }

    col_sim, col_submit = st.columns(2)
    sim_btn = col_sim.form_submit_button("💡 Simuler allocation")
    submitted = col_submit.form_submit_button("Ajouter acheteur")

    # -----------------------------
    # Simulation – n’impacte pas le vrai auto-bid
    # -----------------------------
    if sim_btn and buyer_name:
        temp_buyers = copy.deepcopy(st.session_state.buyers
