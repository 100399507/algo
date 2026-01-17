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

if "sim_result" not in st.session_state:
    st.session_state.sim_result = None

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
            min_value=p["seller_moq"],
            value=p["seller_moq"],
            step=p["volume_multiple"]
        )

        # Déterminer prix minimum = max des prix déjà proposés
        current_max_price = max([b["products"][p["id"]]["current_price"] for b in st.session_state.buyers], default=p["starting_price"])
        price = st.number_input(
            f"Prix souhaité – {p['id']}",
            min_value=current_max_price + 0.01,
            value=current_max_price + 0.01,
            step=0.01
        )

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=price + 1.0,
            step=0.01
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    submitted_sim = st.form_submit_button("💡 Simuler mon allocation")
    submitted_add = st.form_submit_button("➕ Ajouter acheteur")

    if submitted_sim and buyer_name:
        temp_buyers = st.session_state.buyers + [{
            "name": buyer_name,
            "products": buyer_products,
            "auto_bid": auto_bid
        }]
        # Auto-bid uniquement pour le nouvel acheteur
        temp_buyers = run_auto_bid_aggressive(temp_buyers, products)
        sim_alloc, _ = solve_model(temp_buyers, products)
        # Vérifie si le nouvel acheteur obtient de l'allocation
        new_alloc = {pid: sim_alloc[buyer_name][pid] for pid in buyer_products}
        st.session_state.sim_result = {
            "buyer_name": buyer_name,
            "allocations": new_alloc
        }
        st.success(f"Simulation effectuée pour {buyer_name}.")
        for pid, qty_alloc in new_alloc.items():
            if qty_alloc > 0:
                st.info(f"✅ {pid}: position gagnante ({qty_alloc} allouée)")
            else:
                st.warning(f"❌ {pid}: position perdante. Augmenter le prix pour être positionné")

    if submitted_add and buyer_name:
        # Si simulation gagnante ou non, ajoute toujours
        st.session_state.buyers.append({
            "name": buyer_name,
            "products": buyer_products,
            "auto_bid": auto_bid
        })
        # Auto-bid pour tous
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        snapshot(f"Ajout acheteur + auto-bid {buyer_name}")
        st.success(f"Acheteur {buyer_name} ajouté et allocation mise à jour.")
        st.session_state.sim_result = None  # reset simulation après ajout

# -----------------------------
# Reset Sidebar
# -----------------------------
if st.sidebar.button("🔄 Reset tout"):
    st.session_state.buyers = []
    st.session_state.history = []
    st.session_state.sim_result = None

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
    if st.button("🧹 Reset allocations"):
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

    selected = st.selectbox(
        "Voir détail itération",
        options=range(len(st.session_state.history)),
        format_func=lambda x: f"{x} – {st.session_state.history[x]['label']}"
    )

    hist = st.session_state.history[selected]
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
                "Quantité désirée": qty_desired,
                "MOQ": moq,
                "Quantité allouée": qty_alloc,
                "Prix actuel": current_price,
                "Prix max": max_price,
                "Position": position,
                "CA ligne": qty_alloc * current_price
            })
    detail_df = pd.DataFrame(detail_rows)
    def highlight_position(row):
        return ["background-color: #d4edda" if row["Position"]=="Gagnant" else "background-color: #f8d7da"] * len(row)
    st.dataframe(detail_df.style.apply(highlight_position, axis=1), use_container_width=True)
else:
    st.info("Aucune itération enregistrée")
