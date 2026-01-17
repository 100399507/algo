import streamlit as st
import pandas as pd
import copy

from allocation_algo import (
    solve_model,
    run_auto_bid_aggressive
)
from products_config import products, SELLER_GLOBAL_MOQ

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Allocation Engine – Test UI",
    layout="wide"
)

# =========================================================
# SESSION STATE
# =========================================================
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# =========================================================
# HELPERS
# =========================================================
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
                "Auto-bid": b["auto_bid"]
            })
    return pd.DataFrame(rows)

# =========================================================
# SIDEBAR – ADD BUYER
# =========================================================
st.sidebar.title("➕ Ajouter un acheteur")

with st.sidebar.form("add_buyer"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}

    for p in products:
        st.markdown(f"### {p['name']} ({p['id']})")

        volume_multiple = p["volume_multiple"]

        # -----------------------------
        # Quantité (multiple imposé)
        # -----------------------------
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=0,
            step=volume_multiple,
            value=volume_multiple * 5
        )

        # -----------------------------
        # Prix courant > offres existantes
        # -----------------------------
        if st.session_state.buyers:
            existing_prices = [
                b["products"][p["id"]]["current_price"]
                for b in st.session_state.buyers
            ]
            min_price_allowed = max(existing_prices) + 0.1
        else:
            min_price_allowed = p["starting_price"]

        price = st.number_input(
            f"Prix courant – {p['id']}",
            min_value=min_price_allowed,
            value=min_price_allowed,
            step=0.05
        )

        # -----------------------------
        # Prix max basé sur max existants
        # -----------------------------
        if st.session_state.buyers:
            existing_max_prices = [
                b["products"][p["id"]]["max_price"]
                for b in st.session_state.buyers
            ]
            recommended_max = max(existing_max_prices) + 0.5
        else:
            recommended_max = price

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=recommended_max,
            step=0.05
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

        # -----------------------------
        # Suggestions intelligentes
        # -----------------------------
        st.caption(f"💡 Prix conseillé pour gagner : ≥ {recommended_max:.2f} €")
        st.caption(f"📦 Quantité recommandée : ≥ {p['seller_moq']}")

        # -----------------------------
        # Badge position gagnante / perdante
        # -----------------------------
        if buyer_name:
            simulated_buyers = copy.deepcopy(st.session_state.buyers)
            simulated_buyers.append({
                "name": buyer_name,
                "products": buyer_products,
                "auto_bid": auto_bid
            })

            try:
                allocs, _ = solve_model(simulated_buyers, products)
                alloc_qty = allocs.get(buyer_name, {}).get(p["id"], 0)

                if alloc_qty > 0:
                    st.success("🟢 Position gagnante (stock alloué)")
                else:
                    st.warning("🔴 Position perdante (pas de stock)")
            except:
                st.info("ℹ️ Simulation en attente")

    simulate = st.form_submit_button("🔍 Simuler allocation")
    submitted = st.form_submit_button("Ajouter acheteur")

# =========================================================
# SIMULATION AVANT AJOUT
# =========================================================
if simulate and buyer_name:
    simulated_buyers = copy.deepcopy(st.session_state.buyers)
    simulated_buyers.append({
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    })

    allocs, ca = solve_model(simulated_buyers, products)

    st.sidebar.subheader("📊 Simulation")
    rows = []
    for pid, qty in allocs.get(buyer_name, {}).items():
        price = buyer_products[pid]["current_price"]
        rows.append({
            "Produit": pid,
            "Quantité allouée": qty,
            "Prix": price,
            "CA": qty * price
        })

    st.sidebar.dataframe(pd.DataFrame(rows))
    st.sidebar.metric("💰 CA estimé", f"{ca:.2f} €")

# =========================================================
# AJOUT ACHETEUR
# =========================================================
if submitted and buyer_name:
    st.session_state.buyers.append({
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    })

    st.session_state.buyers = run_auto_bid_aggressive(
        st.session_state.buyers,
        products
    )

    snapshot(f"Ajout acheteur + auto-bid {buyer_name}")
    st.sidebar.success("Acheteur ajouté avec succès")

# =========================================================
# MAIN – DATA VIEW
# =========================================================
st.title("🧪 Interface de test – Allocation multi-acheteurs")

st.subheader("📦 Produits")
st.dataframe(pd.DataFrame(products), use_container_width=True)

st.subheader("👥 Acheteurs")
if st.session_state.buyers:
    st.dataframe(buyers_to_df(), use_container_width=True)
else:
    st.info("Aucun acheteur")

# =========================================================
# ALLOCATION COURANTE
# =========================================================
if st.session_state.history:
    last = st.session_state.history[-1]

    st.subheader("📊 Allocation actuelle")
    rows = []

    for buyer in last["buyers"]:
        for pid, qty in last["allocations"][buyer["name"]].items():
            price = buyer["products"][pid]["current_price"]
            rows.append({
                "Acheteur": buyer["name"],
                "Produit": pid,
                "Quantité": qty,
                "Prix": price,
                "CA": qty * price
            })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.metric("💰 CA total", f"{last['total_ca']:.2f} €")

# =========================================================
# HISTORIQUE
# =========================================================
st.subheader("🕒 Historique")

if st.session_state.history:
    hist_df = pd.DataFrame([
        {
            "Itération": i,
            "Label": h["label"],
            "Acheteurs": len(h["buyers"]),
            "CA": h["total_ca"]
        }
        for i, h in enumerate(st.session_state.history)
    ])
    st.dataframe(hist_df, use_container_width=True)
else:
    st.info("Aucune itération")
