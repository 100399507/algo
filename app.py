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
st.sidebar.markdown(f"**MOQ global vendeur à respecter : {SELLER_GLOBAL_MOQ}**")

with st.sidebar.form("add_buyer"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}
    for p in products:
        st.markdown(f"**{p['name']} ({p['id']})**")
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=p["seller_moq"],
            max_value=p["stock"],
            step=p["volume_multiple"],
            value=p["seller_moq"]
        )

        # Initialisation prix proposé compétitif
        other_max_prices = [b["products"][p["id"]]["max_price"] for b in st.session_state.buyers] if st.session_state.buyers else []
        initial_price = max(other_max_prices) + 0.01 if other_max_prices else p["starting_price"]

        price = st.number_input(
            f"Prix proposé – {p['id']}",
            min_value=initial_price,
            value=initial_price,
            step=0.01
        )

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=price,
            step=0.01
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    submitted_sim = st.form_submit_button("💡 Simuler mon allocation")
    submitted_add = st.form_submit_button("➕ Ajouter l’acheteur")

# -----------------------------
# Simulation Allocation
# -----------------------------
if submitted_sim and buyer_name:
    sim_buyers = st.session_state.buyers + [{
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    }]
    sim_result_buyers = run_auto_bid_aggressive(sim_buyers, products)
    allocations, total_ca = solve_model(sim_result_buyers, products)

    st.session_state.sim_result = {
        "buyer_name": buyer_name,
        "products": buyer_products,
        "allocations": allocations[buyer_name],
        "total_ca": total_ca,
        "buyers": sim_result_buyers
    }

    st.subheader("📊 Résultat simulation")
    for pid, qty in allocations[buyer_name].items():
        current_price = sim_result_buyers[-1]["products"][pid]["current_price"]
        status = "Gagnant ✅" if qty > 0 else "Perdant ❌"
        st.write(f"{pid} – Qté allouée : {qty}, Prix courant : {current_price:.2f}, {status}")

    # Si perdant, afficher prix recommandé pour entrer
    for pid, qty in allocations[buyer_name].items():
        if qty == 0:
            rec = calculate_recommendations(st.session_state.buyers, products, buyer_name)[pid]
            st.info(f"Pour être positionné sur {pid}, augmenter prix ≥ {rec['min_price_to_enter']:.2f} €")

# -----------------------------
# Ajouter Acheteur
# -----------------------------
if submitted_add and buyer_name:
    st.session_state.buyers.append({
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    })
    st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
    snapshot(f"Ajout acheteur + auto-bid {buyer_name}")
    st.success("Acheteur ajouté et auto-bid exécuté")

    # Réinitialiser simulation
    st.session_state.sim_result = None

# -----------------------------
# Reset Buyers
# -----------------------------
if st.sidebar.button("🧹 Reset tout"):
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

col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Lancer allocation"):
        snapshot("Allocation manuelle")

with col2:
    if st.button("🤖 Auto-bid agressif"):
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
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

    st.json({
        "allocations": hist["allocations"],
        "buyers": [
            {
                "name": b["name"],
                "products": {pid: {"current_price": p["current_price"], "max_price": p["max_price"], "qty_desired": p["qty_desired"]} 
                             for pid, p in b["products"].items()}
            } for b in hist["buyers"]
        ]
    })
else:
    st.info("Aucune itération enregistrée")
