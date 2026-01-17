import streamlit as st
import pandas as pd
import copy
from allocation_algo import solve_model, run_auto_bid_aggressive, calculate_recommendations
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

        # Quantité min = MOQ produit, max = stock disponible
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=p["seller_moq"],
            max_value=p["stock"],
            value=p["seller_moq"],
            step=p["volume_multiple"]
        )

        # Prix minimum = supérieur aux current_price existants
        other_current_prices = [
            b["products"][p["id"]]["current_price"]
            for b in st.session_state.buyers if p["id"] in b["products"]
        ]
        min_allowed_price = max(other_current_prices, default=p["starting_price"]) + 0.01

        current_price = st.number_input(
            f"Prix proposé – {p['id']}",
            min_value=min_allowed_price,
            value=min_allowed_price,
            step=0.01
        )

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=current_price,
            value=current_price,  # valeur fixe
            step=0.01
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": current_price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    simulate = st.form_submit_button("Simuler mon allocation")
    add_buyer_btn = st.form_submit_button("Ajouter acheteur")

    if simulate and buyer_name:
        temp_buyers = copy.deepcopy(st.session_state.buyers)
        temp_buyers.append({
            "name": buyer_name,
            "products": copy.deepcopy(buyer_products),
            "auto_bid": auto_bid
        })
        temp_buyers = run_auto_bid_aggressive(temp_buyers, products)
        allocations, _ = solve_model(temp_buyers, products)

        sim_rows = []
        for pid, p in buyer_products.items():
            qty_alloc = allocations[buyer_name][pid]
            status = "Gagnant" if qty_alloc > 0 else "Perdant"
            sim_rows.append({
                "Produit": pid,
                "Quantité souhaitée": p["qty_desired"],
                "Quantité allouée": qty_alloc,
                "Prix proposé": p["current_price"],
                "Statut": status
            })
        st.subheader("📊 Simulation allocation")
        st.dataframe(pd.DataFrame(sim_rows), use_container_width=True)

        # Suggestions si perdant
        for pid, row in zip(buyer_products.keys(), sim_rows):
            if row["Statut"] == "Perdant":
                rec = calculate_recommendations(st.session_state.buyers, products, buyer_name)
                st.info(f"Produit {pid}: pour être positionné, proposer au moins {rec[pid]['recommended_price']:.2f} €")

    if add_buyer_btn and buyer_name:
        st.session_state.buyers.append({
            "name": buyer_name,
            "products": copy.deepcopy(buyer_products),
            "auto_bid": auto_bid
        })
        # Auto-bid agressif après ajout
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        snapshot(f"Ajout acheteur {buyer_name}")
        st.success("Acheteur ajouté et auto-bid exécuté")

# -----------------------------
# Sidebar – Reset
# -----------------------------
if st.sidebar.button("🔄 Reset acheteurs"):
    st.session_state.buyers = []
    st.session_state.history = []

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

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Lancer allocation"):
        snapshot("Allocation manuelle")

with col2:
    if st.button("🤖 Auto-bid agressif"):
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        snapshot("Auto-bid")

with col3:
    if st.button("🧹 Reset tout"):
        st.session_state.buyers = []
        st.session_state.history = []

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
                "CA ligne": qty * current_price
            })
    st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True)
    st.metric("💰 Chiffre d'affaires total", f"{last['total_ca']:.2f} €")

# -----------------------------
# History & Analysis
# -----------------------------
st.subheader("🕒 Historique des itérations")
if st.session_state.history:
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

    selected = st.selectbox("Voir détail itération", options=range(len(st.session_state.history)))
    hist = st.session_state.history[selected]

    # Détail joli tableau
    detail_rows = []
    for b in hist["buyers"]:
        for pid, qty in hist["allocations"][b["name"]].items():
            detail_rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Qté souhaitée": b["products"][pid]["qty_desired"],
                "Qté allouée": qty,
                "Prix courant": b["products"][pid]["current_price"],
                "Prix max": b["products"][pid]["max_price"]
            })
    st.subheader("📄 Détail itération")
    st.dataframe(pd.DataFrame(detail_rows), use_container_width=True)
else:
    st.info("Aucune itération enregistrée")
