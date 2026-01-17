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
        # Quantité initialisée au MOQ produit, min = MOQ
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=p["seller_moq"],
            value=p["seller_moq"],
            step=p["volume_multiple"]
        )
        # Prix courant initial
        current_price = st.number_input(
            f"Prix proposé – {p['id']}",
            min_value=0.0,
            value=p["starting_price"],
            step=0.01
        )
        # Prix max fixe choisi par l'acheteur
        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=current_price,
            value=current_price,  # commence égal au prix courant saisi
            step=0.01
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": current_price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    submitted = st.form_submit_button("Ajouter acheteur")
    
    if submitted and buyer_name:
        st.session_state.buyers.append({
            "name": buyer_name,
            "products": buyer_products,
            "auto_bid": auto_bid
        })
    
        # 🔁 Auto-bid agressif immédiatement après ajout
        st.session_state.buyers = run_auto_bid_aggressive(
            st.session_state.buyers,
            products
        )
    
        snapshot(f"Ajout acheteur + auto-bid {buyer_name}")
        st.success("Acheteur ajouté et auto-bid exécuté")

# -----------------------------
# Sidebar – Reset
# -----------------------------
if st.sidebar.button("🧹 Reset tout"):
    st.session_state.buyers = []
    st.session_state.history = []
    st.sidebar.success("Données réinitialisées")

# -----------------------------
# Main – Data Overview
# -----------------------------
st.title("🧪 Interface de test – Allocation multi-acheteurs")

st.subheader("📦 Produits")
st.dataframe(pd.DataFrame(products), use_container_width=True)

st.subheader("👥 Acheteurs")
if st.session_state.buyers:
    st.dataframe(buyers_to_df(), use_container_width=True)
else:
    st.info("Aucun acheteur pour le moment")

# -----------------------------
# Allocation Controls
# -----------------------------
st.subheader("⚙️ Actions")

col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Lancer allocation"):
        snapshot("Allocation manuelle")

with col2:
    if st.button("🤖 Auto-bid agressif"):
        st.session_state.buyers = run_auto_bid_aggressive(
            st.session_state.buyers, products
        )
        snapshot("Auto-bid")

# -----------------------------
# Current Allocation
# -----------------------------
if st.session_state.history:
    last = st.session_state.history[-1]

    st.subheader("📊 Allocation actuelle")
    alloc_rows = []

    for buyer_data in last["buyers"]:
        buyer_name = buyer_data["name"]
        for pid, qty in last["allocations"][buyer_name].items():
            current_price = buyer_data["products"][pid]["current_price"]
    
            alloc_rows.append({
                "Acheteur": buyer_name,
                "Produit": pid,
                "Quantité allouée": qty,
                "Prix courant": current_price,
                "Prix max": buyer_data["products"][pid]["max_price"],
                "CA ligne": qty * current_price
            })

    st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True)
    st.metric("💰 Chiffre d'affaires total", f"{last['total_ca']:.2f} €")

# -----------------------------
# History & Analysis – Détail itération
# -----------------------------
st.subheader("🕒 Historique des itérations")

if st.session_state.history:
    # Vue synthétique des itérations
    history_df = pd.DataFrame([
        {
            "Itération": i,
            "Label": h["label"],
            "Acheteurs": len(h["buyers"]),
            "CA": h["total_ca"]
        }
        for i, h in enumerate(st.session_state.history)
    ])
    st.dataframe(history_df, use_container_width=True)

    # Choix d'une itération à détailler
    selected = st.selectbox(
        "Voir détail itération",
        options=range(len(st.session_state.history)),
        format_func=lambda x: f"{x} – {st.session_state.history[x]['label']}"
    )

    hist = st.session_state.history[selected]

    # Construction DataFrame détaillé
    detail_rows = []
    for buyer_data in hist["buyers"]:
        buyer_name = buyer_data["name"]
        for pid, qty_alloc in hist["allocations"][buyer_name].items():
            current_price = buyer_data["products"][pid]["current_price"]
            max_price = buyer_data["products"][pid]["max_price"]
            qty_desired = buyer_data["products"][pid]["qty_desired"]
            moq = buyer_data["products"][pid]["moq"]
            position = "Gagnant" if qty_alloc > 0 else "Perdant"

            detail_rows.append({
                "Acheteur": buyer_name,
                "Produit": pid,
                "Qté désirée": qty_desired,
                "MOQ": moq,
                "Qté allouée": qty_alloc,
                "Prix actuel": current_price,
                "Prix max": max_price,
                "Position": position,
                "CA ligne": qty_alloc * current_price
            })

    detail_df = pd.DataFrame(detail_rows)

    # Coloration conditionnelle gagnant/perdant
    def highlight_position(row):
        if row["Position"] == "Gagnant":
            return ["background-color: #d4edda"] * len(row)
        else:
            return ["background-color: #f8d7da"] * len(row)

    st.dataframe(detail_df.style.apply(highlight_position, axis=1), use_container_width=True)
else:
    st.info("Aucune itération enregistrée")
